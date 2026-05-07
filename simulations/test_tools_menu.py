import asyncio
from base_sim import SimulationBase

async def run_simulation():
    sim = SimulationBase("test_tools.db")
    sim.setup_user()
    
    print("\n--- Simulation: Business Tools Flow ---")
    await sim.send_text("Hi")
    await sim.click_button("🛠️ Business Tools")
    
    print("\n--- Testing 'Stats' Command ---")
    await sim.send_text("Stats")
    
    print("\n--- Testing 'Advice' Flow ---")
    await sim.send_text("Advice")
    sim.print_state()
    
    await sim.send_text("How can I increase my profit?")
    sim.print_state()

    print("\n--- Simulation Complete ---")

if __name__ == "__main__":
    asyncio.run(run_simulation())
