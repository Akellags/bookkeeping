import asyncio
import random
from tests.integration.base_integration import IntegrationBase

async def run_integration():
    it = IntegrationBase()
    it.setup_real_user()
    
    test_amount = round(random.uniform(1000, 2000), 1)
    
    print(f"\n--- End-to-End INTEGRATION TEST: Purchase (Amount: {test_amount}) ---")
    
    # 1. Start flow
    await it.send_text("Hi")
    
    # 2. Select Money Out
    await it.click_button("Money Out")
    
    # 3. Select Purchase
    await it.click_button("Purchase")
    
    # 4. Provide details
    await it.send_text(f"Purchased stock worth {test_amount} from Global Traders")
    
    # 5. Select B2C
    await it.click_button("B2C")
    
    # 6. Confirm
    await it.click_button("Confirm")
    
    # 7. Mark as Paid
    await it.click_button("Paid")
    
    # 8. Verify in Google Sheet
    it.check_sheet_for_row("Purchases", test_amount)

if __name__ == "__main__":
    asyncio.run(run_integration())
