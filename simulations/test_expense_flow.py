import asyncio
from base_sim import SimulationBase

async def run_simulation():
    sim = SimulationBase("test_expense.db")
    sim.setup_user()
    
    print("\n--- Simulation: Expense Flow (Menu First) ---")
    await sim.send_text("Hi")
    await sim.click_button("💸 Money Out")
    await sim.click_button("Expense")
    sim.print_state()
    
    await sim.send_text("Paid 5000 for office rent")
    sim.print_state()
    
    await sim.click_button("Confirm")
    await sim.click_button("Paid")
    sim.print_state()

    print("\n--- Simulation: Expense Flow (Direct Entry First) ---")
    # Reset state by sending Hi
    await sim.send_text("Hi")
    
    await sim.send_text("Paid 5000 for office rent")
    sim.print_state()
    
    await sim.click_button("💸 Money Out")
    sim.print_state()
    
    # After clicking Money Out, it should know it's an Expense from AI and ask for confirmation
    await sim.click_button("Confirm")
    await sim.click_button("Paid")
    sim.print_state()

    print("\n--- Simulation Complete ---")

if __name__ == "__main__":
    asyncio.run(run_simulation())
