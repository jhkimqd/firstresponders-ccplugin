# Gas Fees on Polygon PoS

## Overview

Gas fees on Polygon PoS are paid in POL (formerly MATIC) and are significantly lower than Ethereum mainnet. Typical transactions cost fractions of a cent.

## How Gas Works on Polygon PoS

Gas on Polygon PoS works the same way as Ethereum since Polygon is EVM-compatible:

- **Gas Limit**: Maximum amount of gas units a transaction can consume
- **Gas Price**: Price per gas unit in Gwei (1 Gwei = 0.000000001 POL)
- **Transaction Fee**: Gas Used x Gas Price

## Current Gas Price Ranges

| Priority | Gas Price (Gwei) | Typical Cost (USD) |
|----------|-----------------|-------------------|
| Slow | ~30 | < $0.001 |
| Standard | ~50 | < $0.001 |
| Fast | ~80-100 | < $0.01 |
| During congestion | 100-500+ | $0.01 - $0.10 |

## EIP-1559 on Polygon

Polygon PoS supports EIP-1559 (London fork):

- **Base Fee**: Algorithmically determined, burned after each transaction
- **Priority Fee (Tip)**: Goes to validators as an incentive
- **Max Fee**: Maximum total fee you're willing to pay

```javascript
// EIP-1559 transaction example
const tx = {
  to: recipientAddress,
  value: ethers.parseEther("1.0"),
  maxFeePerGas: ethers.parseUnits("100", "gwei"),
  maxPriorityFeePerGas: ethers.parseUnits("30", "gwei"),
};
```

## Estimating Gas

### Using ethers.js

```javascript
const provider = new ethers.JsonRpcProvider("https://polygon-rpc.com");

// Get current gas price
const feeData = await provider.getFeeData();
console.log("Gas Price:", ethers.formatUnits(feeData.gasPrice, "gwei"), "Gwei");

// Estimate gas for a transaction
const gasEstimate = await provider.estimateGas({
  to: recipientAddress,
  data: contractCallData,
});
console.log("Estimated gas:", gasEstimate.toString());
```

### Using the RPC Directly

```bash
# Get current gas price
curl -X POST https://polygon-rpc.com \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_gasPrice","params":[],"id":1}'

# Estimate gas
curl -X POST https://polygon-rpc.com \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_estimateGas","params":[{"to":"0x...","data":"0x..."}],"id":1}'
```

## Gas Optimization Tips

1. **Batch transactions** when possible to amortize the base gas cost
2. **Use efficient data structures** in smart contracts (mappings over arrays)
3. **Minimize storage writes** — storage operations are the most expensive
4. **Use events instead of storage** for data that doesn't need on-chain access
5. **Optimize Solidity code** — use `uint256` instead of smaller types, pack structs
6. **Deploy during low-traffic periods** for the lowest gas prices

## Getting POL for Gas

- **Faucets (Testnet)**: https://faucet.polygon.technology for Amoy testnet POL
- **Bridges**: Bridge ETH/MATIC from Ethereum to Polygon
- **Exchanges**: Buy POL directly on exchanges and withdraw to Polygon
- **Gasless Transactions**: Some dApps sponsor gas via meta-transactions or ERC-4337 account abstraction

## Monitoring Gas Prices

- **Polygonscan Gas Tracker**: https://polygonscan.com/gastracker
- **Polygon Gas Station API**: Provides real-time gas price estimates
