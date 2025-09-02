def get_motivation_text(rep_count: int) -> str:
    """
    Returns a motivational message combining rep count with a consistent message.
    Uses rep_count to deterministically select message to avoid spam.
    
    Args:
        rep_count: Current repetition number
        position: Exercise position/type (currently unused but kept for compatibility)
    
    Returns:
        Formatted motivational string with rep count and consistent message
    """
    
    motivational_messages = [
        "Keep pushing, you're strong!",
        "Strong and steady wins!",
        "Feel the burn now!",
        "One more, then another!",
        "Warrior spirit never quits!",
        "You're crushing it today!",
        "Power through, stay focused!",
        "Champions never give up!",
        "Stronger with every rep!",
        "Mind over matter always!",
        "Push your limits higher!",
        "Sweat now, shine later!",
        "Unstoppable force in motion!",
        "Every rep builds greatness!",
        "Fire burns within you!",
        "Transform pain into strength!",
        "Victory is earned daily!",
        "Relentless pursuit of excellence!",
        "Break barriers, exceed expectations!",
        "Beast mode is activated!"
    ]
    
    # Use rep_count to deterministically select message (cycles through all 20)
    message_index = (rep_count - 1) % len(motivational_messages)
    selected_message = motivational_messages[message_index]
    
    # Combine rep count with motivational message
    return f"Rep {rep_count} - {selected_message}"