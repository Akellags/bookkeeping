import asyncio
import os
from base_integration import IntegrationBase

async def run_integration():
    # Use a unique amount so we don't confuse it with previous test runs
    import random
    test_amount = 777.0 + random.randint(1, 100)
    
    it = IntegrationBase("integration_sale.db")
    it.setup_real_user()
    
    print(f"\n--- End-to-End INTEGRATION TEST: Sale B2B (Amount: {test_amount}) ---")
    
    # 1. GREETING
    print("Step 1: Greeting...")
    await it.send_text("Hi")
    
    # 2. SELECT BUCKET
    print("Step 2: Bucket Selection...")
    await it.click_button("💰 Money In")
    
    # 3. SELECT TYPE
    print("Step 3: Type Selection...")
    await it.click_button("Sale")
    
    # 4. SEND REAL TEXT DETAILS (Uses Real AI)
    print("Step 4: AI Details...")
    await it.send_text(f"Sold goods worth {test_amount} to Acme Corp")
    
    # 5. SELECT SUBTYPE
    print("Step 5: Subtype Selection...")
    await it.click_button("B2B")
    
    # 6. PROVIDE GSTIN (Required for B2B)
    print("Step 6: GSTIN Selection...")
    await it.send_text("37ABCDE1234F1Z5")
    
    # 7. CONFIRM (Appends to Real Google Sheet)
    print("Step 7: Confirming (SLOW STEP - GOOGLE API)...")
    await it.click_button("Confirm")
    
    # 8. MARK PAID
    print("Step 8: Payment Marking...")
    await it.click_button("Paid")
    
    # 9. VERIFY IN GOOGLE SHEET
    print("Step 9: Verification (SLOW STEP - GOOGLE API)...")
    it.check_sheet_for_row("Sales", test_amount)
    
    print("\n--- Integration Test Complete ---")

if __name__ == "__main__":
    asyncio.run(run_integration())
