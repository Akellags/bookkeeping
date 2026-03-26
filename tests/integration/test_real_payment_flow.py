import asyncio
import random
from tests.integration.base_integration import IntegrationBase

async def run_integration():
    it = IntegrationBase()
    it.setup_real_user()
    
    test_amount = round(random.uniform(5000, 10000), 1)
    
    print(f"\n--- End-to-End INTEGRATION TEST: Payment (Amount: {test_amount}) ---")
    
    # 1. Start flow
    await it.send_text("Hi")
    
    # 2. Select Money Out
    await it.click_button("Money Out")
    
    # 3. Select Payment Made
    await it.click_button("Payment Made")
    
    # 4. Provide details
    await it.send_text(f"Payment of {test_amount} to Landlord for rent")
    
    # 5. Select Subtype (Single/Recurring)
    await it.click_button("Single")
    
    # 6. Confirm
    await it.click_button("Confirm")
    
    # 7. Verify in Google Sheet
    await it.check_sheet_for_row("Payments", test_amount)

if __name__ == "__main__":
    asyncio.run(run_integration())
