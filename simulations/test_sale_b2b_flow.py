import os
import sys
import asyncio
from base_sim import SimulationBase

async def run_simulation():
    sim = SimulationBase("test_sale_b2b.db")
    sim.setup_user()
    
    print("\n--- Simulation: Sale B2B Flow ---")
    
    # 1. GREETING
    await sim.send_text("Hi")
    sim.print_state()
    
    # 2. SELECT MONEY IN
    await sim.click_button("💰 Money In")
    sim.print_state()
    
    # 3. SELECT SALE
    await sim.click_button("Sale")
    sim.print_state()
    
    # 4. SEND DETAILS (The bot should be in AWAITING_DETAILS)
    await sim.send_text("Sold items for 1500 to ABC Corp")
    sim.print_state()
    
    # 5. SELECT B2B (The bot should be in PENDING_SUBTYPE)
    await sim.click_button("B2B")
    sim.print_state()
    
    # 6. PROVIDE GSTIN (The bot should be in AWAITING_GSTIN)
    await sim.send_text("37ABCDE1234F1Z5")
    sim.print_state()
    
    # 7. CONFIRM (The bot should be in PENDING_CONFIRM)
    await sim.click_button("Confirm")
    sim.print_state()
    
    # 8. MARK AS PAID (The bot should be in AWAITING_PAYMENT)
    await sim.click_button("Paid")
    sim.print_state()
    
    print("\n--- Simulation Complete ---")

if __name__ == "__main__":
    asyncio.run(run_simulation())
