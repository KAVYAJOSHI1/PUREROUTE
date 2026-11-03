# Hardware Playbook — Step 1: 10-Minute Leak Test Protocol

## Objective
Verify the water loop is 100% leak-free under pump pressure before any microcontroller or electronic circuit is placed on or near the board.

## Equipment Setup
1. Reservoir filled with clean tap water (never salt or soil in this loop).
2. Submersible mini pump (3-6V) submerged at bottom of reservoir. Cable joint dry and suspended above waterline.
3. Clear flexible tubing clamped securely at:
   - Pump outlet
   - Flow sensor inlet and outlet (observe directional arrow)
   - Tee-junction to manometer tube
   - Sealed cartridge jar inlet (bottom of jar)
   - Cartridge jar outlet (top stub) returning to reservoir above waterline.
4. Manometer clear vertical tube (30 cm) open to air at top, attached with tape to a vertical millimeter ruler.

## Leak Test Execution
1. Electronics must remain completely disconnected and parked safely away (>15 cm).
2. Wrap clean white paper towels around every tube joint, barb, tee, and jar lid seam.
3. Power the pump directly from the 5V 2A auxiliary adapter.
4. Run continuously for **10 full minutes**.

## Pass Criteria
- [ ] No water drips, moisture rings, or weeping on any paper towel.
- [ ] Steady water jet returning to reservoir with zero spitting/air-surging.
- [ ] Jar lid silicone gasket holds pressure without bowing or seeping.
- [ ] Manometer column establishes a steady baseline height (approx. 5-7 cm).
