# Staked POL (sPOL) — Polygon's Liquid Staking Token

> **Authoritative sources.**
> - Contracts (audited, actively maintained): [`0xPolygon/sPOL-contracts`](https://github.com/0xPolygon/sPOL-contracts)
> - Launch announcement (2026-04-14): https://polygon.technology/blog/were-launching-spol-to-bring-better-rewards-to-polygon-stakers
> - User entry point: https://staking.polygon.technology
> - Audits (in-repo): ChainSecurity (Polygon sPOL) and Certora (Polygon sPOL staking) under `audits/` in the contracts repo.

## What sPOL is

sPOL is Polygon's native **liquid staking token** for POL, launched 2026-04-14. A user deposits POL into the sPOL protocol on Ethereum and receives sPOL — a transferable ERC-20 that represents a proportional share of the staked pool. The POL stays staked (delegated to participating validators) and continues earning rewards, but the user holds a composable ERC-20 they can use in DeFi.

### Problem it addresses

- Over 3.6B POL is staked, but only 4–5% of staking participation previously existed as liquid staking tokens — the rest is capital locked out of DeFi.
- Third-party LSTs on Polygon historically charged 5–16% fees, creating weak incentives.
- Native liquid staking directs a share of priority fees from participating validators back to sPOL holders.

## Key properties for stakers

- **Auto-compounding**: rewards accrue via a rising sPOL↔POL exchange rate, not a rebasing balance. Users hold a fixed number of sPOL; its redemption value in POL grows over time.
- **Composable**: sPOL is a plain ERC-20 (with EIP-2612 permit). Usable as collateral or LP without waiting for unbonding.
- **Cross-chain**: sPOL is bridged to Polygon PoS as `sPOLChild`, with cached exchange-rate updates relayed via the protocol's cross-chain messenger.
- **Priority-fee share**: validators participating in the sPOL program agree to return a portion of priority fees to delegators.
- **Redeemable at any time**: users can redeem sPOL for POL + accrued rewards through the Polygon staking portal at staking.polygon.technology, subject to the protocol's unbonding queue.
- **Day-one liquidity**: Uniswap v4 AMM pools for sPOL/POL went live at launch. Polygon Labs committed 10M POL from treasury on day one and up to 100M progressively to seed liquidity.

## sPOL vs native POL staking

| Dimension | Native POL staking | sPOL |
|---|---|---|
| Capital lock-up | Locked while staked + unbonding delay | Receives transferable sPOL immediately |
| Reward mechanic | Accrues to the validator delegation | Accrues via rising sPOL↔POL exchange rate |
| DeFi composability | None until unstaked | Full — sPOL is an ERC-20 |
| Priority fees | Flow to validator/delegator per validator policy | Participating validators return a share to sPOL holders |
| Validator selection | Delegator picks one or more validators | Pool-level delegation managed by `sPOLController` |
| Fees | Validator commission only | Validator commission + any protocol economics; see contracts for current parameters |

Native staking remains available; sPOL is an additional opt-in path, not a replacement.

## Architecture

Six core contracts (see `sPOL-contracts` for source + interfaces):

| Contract | Layer | Role |
|---|---|---|
| `sPOLController` | L1 (Ethereum) | Validator delegation, POL↔sPOL conversion, reward compounding, unbonding queue |
| `sPOL` | L1 | ERC-20 (EIP-2612 permit); `mint`/`burn` gated to the controller |
| `sPOLMessenger` | L1 | Relays exchange-rate updates, processes cross-chain proofs |
| `sPOLChild` | L2 (Polygon PoS) | L2 sPOL token; supports buy operations using cached exchange rate |
| `PolBridger` | L1 + L2 | Moves POL across the Polygon PoS bridge |
| `MsgCoder` | shared | Cross-chain message encoding/decoding |

High-level flow:

```
Stake:   User → POL → sPOLController (L1) → delegates to validators → user receives sPOL
Rewards: Validator → POL rewards → sPOLController compounds → sPOL↔POL rate rises
Bridge:  sPOL on L1 ⇄ sPOLChild on PoS via messenger + PolBridger
Unstake: User burns sPOL → queued in unbonding → claim POL after delay
```

## Deployment addresses

Verify on-chain before quoting to users; addresses from the `sPOL-contracts` README as of the launch window:

**Ethereum (mainnet)**

| Contract | Address |
|---|---|
| `sPOL` | `0x3B790d651e950497c7723D47B24E6f61534f7969` |
| `sPOLController` | `0xEaadA411F2600570796c341552b9869DA708a28B` |
| `sPOLMessenger` | `0x0356e303B375D5a11D9Eb7d57DBF544FeE6972C9` |
| `PolBridger` | `0x71663898Df7470e3b64d52663Ff975895E9b06E8` |

**Polygon PoS**

| Contract | Address |
|---|---|
| `sPOLChild` | `0xd1CD49A08AeF3Af93457aEc17C786C2b7F48eCd7` |
| `PolBridger` | `0x71663898Df7470e3b64d52663Ff975895E9b06E8` |

Testnet (Sepolia + Amoy) addresses are listed in the contracts README.

## User flow

1. Visit https://staking.polygon.technology with a wallet holding POL on Ethereum.
2. Select the sPOL route.
3. Approve POL and deposit — receive sPOL at the current exchange rate.
4. Optionally bridge sPOL to Polygon PoS via the protocol's messenger or use it directly in L1 DeFi.
5. To unstake: initiate redemption for sPOL → queued in the unbonding queue → claim POL after the delay window.

## Developer / reviewer workflow

Tooling: **Foundry** (with `soldeer` for dependency management). From the contracts repo:

```bash
forge soldeer install
forge build
forge test
forge coverage --no-match-coverage "(script|mocks|msg|integration)"
```

`.env` needs `DEPLOYER_PRIVATE_KEY`, `L1_RPC_URL`, `L2_RPC_URL`.

License: `MIT OR Apache-2.0`.

## Risks and caveats

From the launch announcement:

- **Smart contract risk** — even with ChainSecurity + Certora audits, "no audit eliminates all risk."
- **Slashing risk** — inherited from the validator set the controller delegates to; slashing reduces the pool and therefore the sPOL↔POL exchange rate.
- **Exchange rate risk** — the rate is influenced by rewards and validator performance; it can move in either direction in adverse scenarios.
- **Cross-chain / messenger risk** — exchange-rate updates on PoS depend on the messenger relay; L2 operations use a cached rate.
- **Market/liquidity risk** — AMM pools determine market-clearing prices for sPOL↔POL swaps, which may diverge from the redemption rate.

## First-responder answers

### What is sPOL?
sPOL is Polygon's native liquid staking token for POL. Users deposit POL on Ethereum into the sPOL protocol and receive sPOL, a transferable ERC-20 that represents a share of the pooled, staked POL. sPOL auto-compounds rewards via a rising sPOL-to-POL exchange rate.

### How is sPOL different from native POL staking?
Native POL staking locks capital while staked and during the unbonding delay, with rewards accruing to the validator delegation. sPOL instead issues a transferable ERC-20 immediately; rewards accrue as the sPOL-to-POL redemption rate rises. sPOL is usable in DeFi (collateral, LP) while the underlying POL stays staked. sPOL does not replace native POL staking; both paths remain available.

### How do I get sPOL?
Visit https://staking.polygon.technology with a wallet holding POL on Ethereum, deposit POL, and receive sPOL at the current exchange rate.

### What is the sPOL contract address on Ethereum?
The sPOL ERC-20 token contract address on Ethereum is `0x3B790d651e950497c7723D47B24E6f61534f7969`. Other sPOL addresses on Ethereum: `sPOLController` at `0xEaadA411F2600570796c341552b9869DA708a28B`, `sPOLMessenger` at `0x0356e303B375D5a11D9Eb7d57DBF544FeE6972C9`, `PolBridger` at `0x71663898Df7470e3b64d52663Ff975895E9b06E8`.

### Is sPOL available on Polygon PoS?
Yes, sPOL is available on Polygon PoS. The sPOL token on Polygon PoS is `sPOLChild`, deployed at `0xd1CD49A08AeF3Af93457aEc17C786C2b7F48eCd7`. sPOL on Polygon PoS uses a cached sPOL-to-POL exchange rate relayed from Ethereum.

### What is the sPOL redemption / unbonding delay?
The sPOL redemption delay is governed by the `sPOLController` unbonding queue parameters. Refer to the live contract or the Polygon staking portal at https://staking.polygon.technology for the current value.

### Who audited the sPOL contracts?
ChainSecurity audited Polygon sPOL. Certora audited Polygon sPOL staking. Audit reports live under the `audits/` directory in the `sPOL-contracts` repository at https://github.com/0xPolygon/sPOL-contracts.

### When did sPOL launch?
sPOL launched on 2026-04-14 with day-one Uniswap v4 AMM pools for sPOL/POL liquidity. Polygon Labs committed 10M POL from treasury on day one, with up to 100M POL progressively added to seed sPOL liquidity.

## References

- Contracts: https://github.com/0xPolygon/sPOL-contracts
- Launch post: https://polygon.technology/blog/were-launching-spol-to-bring-better-rewards-to-polygon-stakers
- Staking portal: https://staking.polygon.technology
- POL token info: https://polygon.technology/pol-token
