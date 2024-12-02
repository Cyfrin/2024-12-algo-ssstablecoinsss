import boa
from boa import BoaError
from boa.util.abi import Address
from eth.constants import ZERO_ADDRESS
from eth_utils import to_wei
from hypothesis import assume, settings
from hypothesis import strategies as st
from hypothesis.stateful import (
    RuleBasedStateMachine,
    initialize,
    invariant,
    rule,
)
from moccasin.config import get_active_network
from boa.test.strategies import strategy
from src.mocks import MockV3Aggregator

from script.deploy_dsc import deploy_dsc
from script.deploy_dsc_engine import deploy_dsc_engine

USERS_SIZE = 10
COLLATERAL_SIZE = 2
MAX_DEPOSIT_SIZE = to_wei(1000, "ether")
MAX_NEW_PRICE = 1.01
MIN_NEW_PRICE = 0.4

LIQUIDATOR = boa.env.generate_address()


class StablecoinFuzzer(RuleBasedStateMachine):
    def __init__(self):
        super().__init__()

    @initialize()
    def setup(self):
        self.dsc = deploy_dsc()
        self.dsce = deploy_dsc_engine(self.dsc)
        active_network = get_active_network()

        self.weth = active_network.manifest_named("weth")
        self.wbtc = active_network.manifest_named("weth")
        self.eth_usd = active_network.manifest_named("eth_usd_price_feed")
        self.btc_usd = active_network.manifest_named("btc_usd_price_feed")

        self.users = [Address("0x" + ZERO_ADDRESS.hex())]
        while Address("0x" + ZERO_ADDRESS.hex()) in self.users:
            self.users = [boa.env.generate_address() for _ in range(USERS_SIZE)]

    @rule(
        collateral_seed=st.integers(min_value=0, max_value=1),
        user_seed=st.integers(min_value=0, max_value=USERS_SIZE - 1),
        amount=strategy("uint256", min_value=1, max_value=MAX_DEPOSIT_SIZE),
    )
    def mint_and_deposit(self, amount, collateral_seed, user_seed, user=None):
        collateral = self._get_collateral_from_seed(collateral_seed)
        user = user or self.users[user_seed]
        with boa.env.prank(self.users[user_seed]):
            collateral.mint_amount(amount)
            collateral.approve(self.dsce.address, amount)
            self.dsce.deposit_collateral(collateral, amount)

    @rule(
        collateral_seed=st.integers(min_value=0, max_value=1),
        user_seed=st.integers(min_value=0, max_value=USERS_SIZE - 1),
        percentage=st.integers(min_value=0, max_value=100),
    )
    def redeem_collateral(self, percentage, collateral_seed, user_seed):
        user = self.users[user_seed]
        collateral = self._get_collateral_from_seed(collateral_seed)
        max_redeemable = self.dsce.get_collateral_balance_of_user(user, collateral)
        to_redeem = (max_redeemable * percentage) // 100
        assume(to_redeem > 0)
        with boa.env.prank(user):
            try:
                self.dsce.redeem_collateral(collateral, to_redeem)
            except BoaError as e:
                assert "DSCEngine__BreaksHealthFactor" in str(e.stack_trace[0].vm_error)

    @rule(
        user_seed=st.integers(min_value=0, max_value=USERS_SIZE - 1),
        amount=strategy("uint256", min_value=1, max_value=MAX_DEPOSIT_SIZE),
        collateral_seed=st.integers(min_value=0, max_value=1),
    )
    def mint_dsc(self, user_seed, amount, collateral_seed):
        user = self.users[user_seed]
        with boa.env.prank(user):
            try:
                self.dsce.mint_dsc(amount)
            except BoaError as e:
                if "DSCEngine__BreaksHealthFactor" in str(e.stack_trace[0].vm_error):
                    collateral = self._get_collateral_from_seed(collateral_seed)
                    collateral_amount = self.dsce.get_token_amount_from_usd(
                        collateral.address, amount
                    )
                    if collateral_amount == 0:
                        collateral_amount = 1
                    collateral_amount = collateral_amount * 3
                    self.mint_and_deposit(collateral_amount, collateral_seed, user_seed)
                    self.dsce.mint_dsc(amount)

    @rule(
        percentage_new_price=st.floats(
            min_value=MIN_NEW_PRICE, max_value=MAX_NEW_PRICE
        ),
        collateral_seed=st.integers(min_value=0, max_value=1),
    )
    def update_collateral_price(self, percentage_new_price, collateral_seed):
        collateral = self._get_collateral_from_seed(collateral_seed)
        price_feed = MockV3Aggregator.at(
            self.dsce.token_address_to_price_feed(collateral.address)
        )
        current_price = price_feed.latestAnswer()
        new_price = int(current_price * percentage_new_price)
        price_feed.updateAnswer(new_price)

    @invariant()
    def liquidate(self):
        for user in self.users:
            health_factor = self.dsce.health_factor(user)
            if health_factor < int(1e18):
                print("Liquidating user...")
                total_dsc_minted, total_value_usd = self.dsce.get_account_information(
                    user
                )
                debt_to_cover = total_dsc_minted - total_value_usd
                token_amount = self.dsce.get_token_amount_from_usd(
                    self.weth.address, debt_to_cover
                )
                with boa.env.prank(LIQUIDATOR):
                    self.mint_and_deposit(token_amount, 0, 0, user=user)
                    self.dsce.liquidate(self.weth, user, debt_to_cover)

    @invariant()
    def protocol_must_have_more_value_than_total_supply(self):
        total_supply = self.dsc.totalSupply()

        weth_deposited = self.weth.balanceOf(self.dsce.address)
        wbtc_deposited = self.wbtc.balanceOf(self.dsce.address)

        weth_value = self.dsce.get_usd_value(self.weth, weth_deposited)
        wbtc_value = self.dsce.get_usd_value(self.wbtc, wbtc_deposited)
        assert (weth_value + wbtc_value) >= total_supply

    def _get_collateral_from_seed(self, seed):
        if seed == 0:
            return self.weth
        return self.wbtc


stablecoin_fuzzer = StablecoinFuzzer.TestCase
stablecoin_fuzzer.settings = settings(max_examples=64, stateful_step_count=64)
