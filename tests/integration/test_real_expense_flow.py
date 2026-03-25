import asyncio
import os
from base_integration import IntegrationBase

async def run_integration():
    import random
    test_amount = 555.0 + random.randint(1, 100)
    
    it = IntegrationBase("integration_expense.db")
    it.setup_real_user()
    
    print(f"\n--- End-to-End INTEGRATION TEST: Expense (Amount: {test_amount}) ---")
    
    # 1. DIRECT TEXT ENTRY (Mimics a real power user)
    await it.send_text(f"Paid {test_amount} for office stationary")
    
    # 2. SELECT BUCKET
    await it.click_button("💸 Money Out")
    
    # 3. CONFIRM (Should skip Expense sub-button because AI identified it)
    await it.click_button("Confirm")
    
    # 4. MARK PAID
    await it.click_button("Paid")
    
    # 5. VERIFY IN GOOGLE SHEET
    it.check_sheet_for_row("Expenses", test_amount)
    
    print("\n--- Integration Test Complete ---")

if __name__ == "__main__":
    asyncio.run(run_integration())
