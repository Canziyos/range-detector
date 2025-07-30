from time import ticks_ms


# System configuration / thresholds
# -------------------------------- #
min_dist  = 100
max_dist  = 3_000


# Flags updated by interrupts (shared with main loop)
# -------------------------------------------------- #
sys_on = False            # System ON/OFF state (controlled by buttons)
last_green_press = 0      # Debounce timer for buttons.
last_red_press = 0 
debounce_ms = 300         # (maybe we need two different ones)
last_pir_trigger  = 0     # Debounce timer for PIR.
pir_active = False        # Current PIR state (True = motion detected).

# --------------- #
# Debug printing
VERBOSE = True
def dbg(*parts):
    if VERBOSE:
        print(*parts)


# Interrupt handlers.
# ----------------------------------------------#
def green_irq(pin):
    global last_green_press, sys_on
    now = ticks_ms()
    # Debounce.
    if ticks_ms() - last_green_press < debounce_ms:
        return
    last_green_press = now
    if not sys_on:
        sys_on = True
        dbg("Green => System ON")

def red_irq(pin):
    global last_red_press, sys_on
    now = ticks_ms()
    if ticks_ms() - last_red_press < debounce_ms:
        return
    last_red_press = now
    if sys_on:
        sys_on= False
        dbg("Red => System OFF")

def pir_irq(pin):
    global pir_active, last_pir_trigger

    # Ignore PIR if system is OFF.
    if not sys_on:
        return

    now = ticks_ms()
    # Debounce for PIR  (should be reconsidewred)
    if ticks_ms() - last_pir_trigger < 200:
        return
    last_pir_trigger = now

    pir_active = bool(pin.value())
    dbg(f"IRQ: PIR state changed => {'ACTIVE' if pir_active else 'INACTIVE'}")
