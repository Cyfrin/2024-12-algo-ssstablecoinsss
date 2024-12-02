# First Flight #30 Algo Ssstablecoinsss

- Starts: December 05, 2024 Noon UTC
- Ends: Dec 12, 2024 Noon UTC

- nSLOC:

[//]: # (contest-details-open)

# About

This project is meant to be a stablecoin where users can deposit WETH and WBTC in exchange for a token that will be pegged to the USD. The system is meant to be such that someone could fork this codebase, swap out WETH & WBTC for any basket of assets they like, and the code would work the same.

[//]: # (contest-details-close)

[//]: # (getting-started-open)

# Getting Started

## Prerequisites

- [git](https://git-scm.com/)
  - You'll know you've done it right if you can run `git --version` and see a version number.
- [anvil](https://book.getfoundry.sh/anvil/)
  - You'll know you've done it right if you can run `anvil --version` and see an output like `anvil 0.2.0 (fdd321b 2024-10-15T00:21:13.119600000Z)`
- [era_test_node and zkvyper](https://cyfrin.github.io/moccasin/tutorials/zksync-getting-started.html)
  - You'll know you've done it right if you can run `zkvyper --version` and `era_test_node --version`
- [moccasin](https://github.com/Cyfrin/moccasin)
  - You'll know you've done it right if you can run `mox --version` and get an output like: `Moccasin CLI v0.3.0`

## Installation

```bash
git clone https://github.com/cyfrin/vy-stablecoin
cd vy-stablecoin
mox install
```

## Quickstart

```bash
mox run deploy 
```

# Usage

## Compile

```bash
mox compile --network eravm
```

## Test

```bash
mox test 
```

# Formatting

## Python

```
uv run ruff check --select I --fix
uv run ruff check . --fix
```

## Vyper 

```
uv run mamushi src
```

[//]: # (getting-started-close)

[//]: # (scope-open)

# Scope

```
./src
├── decentralized_stable_coin.vy
├── dsc_engine.vy
└── oracle_lib.vy
```

## Compatibilities

Chains: ZKsync Era
Tokens: WETH and WBTC

[//]: # (scope-close)

[//]: # (known-issues-open)

# Known Issues
The following issues can be ignored.

- A known gas issue, is that we use storage variables instead of immutables for storing the addresses of the collateral. You can ignore this.
- If the protocol ever becomes insolvent, there is almost no way to recover. This is a known issue.
- We don't want the constructor marked as payable, as we like the extra protection it gives us from accidentally deploying a contract with ETH.

[//]: # (known-issues-close)
