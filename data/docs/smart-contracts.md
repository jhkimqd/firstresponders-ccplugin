# Smart Contract Development on Polygon

## EVM Compatibility

Polygon PoS is fully EVM-compatible. Any smart contract that works on Ethereum will work on Polygon without modification. This includes:

- Solidity and Vyper contracts
- All EVM opcodes
- Precompiled contracts
- ERC standards (ERC-20, ERC-721, ERC-1155, ERC-4337, etc.)

## Development Tools

All Ethereum development tools work on Polygon:

| Tool | Description |
|------|-------------|
| Hardhat | Development environment, testing, deployment |
| Foundry | Fast Solidity testing and deployment |
| Remix | Browser-based IDE |
| OpenZeppelin | Audited smart contract libraries |
| Thirdweb | No-code contract deployment |

## Common Contract Patterns

### ERC-20 Token

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

contract MyToken is ERC20 {
    constructor(uint256 initialSupply) ERC20("MyToken", "MTK") {
        _mint(msg.sender, initialSupply * 10 ** decimals());
    }
}
```

### ERC-721 NFT

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

contract MyNFT is ERC721, Ownable {
    uint256 private _nextTokenId;

    constructor() ERC721("MyNFT", "MNFT") Ownable(msg.sender) {}

    function mint(address to) public onlyOwner {
        uint256 tokenId = _nextTokenId++;
        _safeMint(to, tokenId);
    }
}
```

## Gas Optimization for Polygon

While Polygon gas is cheap, optimization still matters for high-volume dApps:

1. **Use `calldata` instead of `memory`** for read-only function parameters
2. **Pack storage variables** — Solidity packs variables smaller than 32 bytes
3. **Use `uint256`** instead of `uint8` for standalone variables (EVM operates on 256-bit words)
4. **Use events for off-chain data** instead of storage
5. **Minimize SSTORE operations** — each storage write costs 20,000+ gas

## Testing on Polygon

### Unit Testing with Hardhat

```javascript
const { expect } = require("chai");

describe("MyToken", function () {
  it("should mint initial supply to deployer", async function () {
    const [owner] = await ethers.getSigners();
    const Token = await ethers.getContractFactory("MyToken");
    const token = await Token.deploy(1000);
    expect(await token.balanceOf(owner.address)).to.equal(
      ethers.parseEther("1000")
    );
  });
});
```

### Testing with Foundry

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Test.sol";
import "../src/MyToken.sol";

contract MyTokenTest is Test {
    MyToken token;

    function setUp() public {
        token = new MyToken(1000);
    }

    function testInitialSupply() public {
        assertEq(token.totalSupply(), 1000 * 1e18);
    }
}
```

## Verifying Contracts on Polygonscan

Always verify your contracts for transparency:

```bash
# Hardhat
npx hardhat verify --network polygon DEPLOYED_ADDRESS constructor_args

# Foundry
forge verify-contract DEPLOYED_ADDRESS MyContract --chain polygon
```

## Security Considerations

- **Reentrancy**: Use OpenZeppelin's `ReentrancyGuard` or checks-effects-interactions pattern
- **Access Control**: Use `Ownable` or `AccessControl` from OpenZeppelin
- **Integer Overflow**: Solidity 0.8+ has built-in overflow checks
- **Front-running**: Be aware of MEV on Polygon — consider commit-reveal schemes
- **Upgradability**: Use transparent proxy or UUPS patterns for upgradeable contracts
- **Audit**: Get your contracts audited before mainnet deployment
