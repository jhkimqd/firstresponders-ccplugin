# Bridging Between Ethereum and Polygon

## Overview

The Polygon PoS Bridge allows you to transfer assets between Ethereum and Polygon PoS. It supports ERC-20, ERC-721, and ERC-1155 tokens.

## Bridge Types

### PoS Bridge

The primary bridge for Polygon PoS:

- **Deposit (Ethereum to Polygon)**: Lock tokens on Ethereum, mint on Polygon. Takes ~7-8 minutes.
- **Withdraw (Polygon to Ethereum)**: Burn tokens on Polygon, claim on Ethereum after checkpoint inclusion. Takes ~30 minutes to 3 hours.

### Third-Party Bridges

Several third-party bridges offer faster bridging:

- **Polygon Portal** (https://portal.polygon.technology) — Official bridge UI
- **Hop Protocol** — Fast cross-chain transfers
- **Across Protocol** — Optimistic bridge with fast finality
- **Stargate (LayerZero)** — Omnichain liquidity transport

## Using the PoS Bridge Programmatically

### Deposit (Ethereum to Polygon)

```javascript
const { POSClient, use } = require("@maticnetwork/maticjs");
const { Web3ClientPlugin } = require("@maticnetwork/maticjs-ethers");

use(Web3ClientPlugin);

const posClient = new POSClient();
await posClient.init({
  network: "mainnet",
  version: "v1",
  parent: { provider: ethereumProvider, defaultConfig: { from: userAddress } },
  child: { provider: polygonProvider, defaultConfig: { from: userAddress } },
});

// Approve token spend
const erc20Token = posClient.erc20(tokenAddress, true);
const approveTx = await erc20Token.approve(amount);
await approveTx.getReceipt();

// Deposit
const depositTx = await erc20Token.deposit(amount, userAddress);
const receipt = await depositTx.getReceipt();
console.log("Deposit tx hash:", receipt.transactionHash);
// Tokens arrive on Polygon in ~7-8 minutes
```

### Withdraw (Polygon to Ethereum)

Withdrawals are a two-step process:

```javascript
// Step 1: Burn tokens on Polygon
const erc20Token = posClient.erc20(tokenAddress);
const burnTx = await erc20Token.withdrawStart(amount);
const burnReceipt = await burnTx.getReceipt();
console.log("Burn tx hash:", burnReceipt.transactionHash);

// Step 2: Wait for checkpoint inclusion (~30 min), then claim on Ethereum
// Check if checkpoint has been included:
const isCheckpointed = await posClient.isCheckPointed(burnReceipt.transactionHash);

if (isCheckpointed) {
  const exitTx = await erc20Token.withdrawExit(burnReceipt.transactionHash);
  const exitReceipt = await exitTx.getReceipt();
  console.log("Exit tx hash:", exitReceipt.transactionHash);
}
```

## Bridging Native POL/MATIC

To bridge native POL (MATIC) tokens:

1. Use the Polygon Portal at https://portal.polygon.technology
2. Connect your wallet
3. Select the amount and direction
4. Approve and confirm the transaction

## Bridge Security

- The PoS Bridge is secured by the validator set (100+ validators)
- Deposits are confirmed after sufficient Ethereum block confirmations
- Withdrawals require checkpoint inclusion on Ethereum
- The bridge contracts are audited and battle-tested

## Common Issues

### Deposit Not Showing on Polygon
- Wait at least 7-8 minutes for the deposit to be processed
- Check the transaction on Etherscan to confirm it was successful
- Use the Polygon Portal to track the status

### Withdrawal Taking Too Long
- Withdrawals require a checkpoint to be submitted to Ethereum (~30 min)
- After checkpoint, you still need to submit the exit transaction on Ethereum
- Check checkpoint status at https://portal.polygon.technology

### Gas Fees
- Deposits require Ethereum gas (paid in ETH)
- Withdrawals require gas on both Polygon (burn) and Ethereum (exit claim)
- Ethereum gas for the exit transaction can be significant during congestion
