import hashlib
import time

class MicroRewardLedger:
    def __init__(self):
        self.chain = []
        self.balances = {"AI_Agent_01": 0.0, "Decentralized_Node_Beta": 0.0}
        # Initialize Genesis Block
        self.create_block(proof=100, previous_hash='0')

    def create_block(self, proof, previous_hash):
        block = {
            'index': len(self.chain) + 1,
            'timestamp': time.time(),
            'proof': proof,
            'previous_hash': previous_hash,
            'transactions': []
        }
        self.chain.append(block)
        return block

    def issue_payment(self, recipient, amount, objective_achieved):
        """Mints and issues a micro-reward payment for verified milestones."""
        if recipient not in self.balances:
            self.balances[recipient] = 0.0
        
        self.balances[recipient] += amount
        print(f"💰 [LEDGER] Issued {amount:.4f} Q-Bio Tokens to {recipient}.")
        print(f"   ↳ Reason: {objective_achieved}")
        print(f"   ↳ New Balance: {self.balances[recipient]:.4f} Tokens\n")

    def hash_block(self, block):
        return hashlib.sha256(str(block).encode()).hexdigest()
