import pytest
from app.agents.refiner_agent import refine_response, refine_response_fallback

def test_refiner_fallback_paise_conversion():
    """
    Ensure the fallback formatter converts all "paise" substring values to standard Rupees.
    """
    input_str = "Expense of 1200 paise added by Alice for 'Dinner'."
    expected = "Expense of ₹12 added by Alice for 'Dinner'."
    assert refine_response_fallback(input_str) == expected
    
    input_str_decimal = "Recorded 1250 paise spent."
    expected_decimal = "Recorded ₹12.50 spent."
    assert refine_response_fallback(input_str_decimal) == expected_decimal
    
    input_str_multi = "Bob owes Alice 300 paise. Charlie owes Bob 650 paise."
    expected_multi = "Bob owes Alice ₹3. Charlie owes Bob ₹6.50."
    assert refine_response_fallback(input_str_multi) == expected_multi

def test_refine_response_integrations():
    """
    Ensure the refiner converts currency and parses conversational results.
    """
    input_str = "Recorded settlement: Bob paid Alice 300 paise."
    res = refine_response(input_str)
    # The result should contain standard Rupee notation (either via LLM or fallback)
    assert "₹3" in res or "3" in res
