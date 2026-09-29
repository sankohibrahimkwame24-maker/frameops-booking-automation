def booking_confirmation_text(client_name: str, scheduled_time: str) -> str:
    return f"""Hey {client_name},

Thanks for booking a FrameOps discovery call for {scheduled_time}.

Before the call, please reply with one or two of your latest video links. I'll take a look beforehand so we can spend the call discussing your actual content workflow rather than starting from zero.

Best,
Ibrahim
Founder, FrameOps
"""
