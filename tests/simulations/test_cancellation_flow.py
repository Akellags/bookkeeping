import asyncio
from base_sim import SimulationBase

async def run_simulation():
    sim = SimulationBase("test_cancel.db")
    sim.setup_user()
    
    print("\n--- Simulation: Cancellation Flow (Mid-Menu) ---")
    await sim.send_text("Hi")
    await sim.click_button("💰 Money In")
    await sim.click_button("Cancel")
    sim.print_state()
    
    print("\n--- Simulation: Cancellation Flow (After Details) ---")
    await sim.send_text("Hi")
    await sim.send_text("Paid 500 for coffee")
    await sim.click_button("💸 Money Out")
    # Bot asks for confirmation here
    await sim.click_button("Cancel")
    sim.print_state()

    print("\n--- Simulation Complete ---")

if __name__ == "__main__":
    asyncio.run(run_simulation())
