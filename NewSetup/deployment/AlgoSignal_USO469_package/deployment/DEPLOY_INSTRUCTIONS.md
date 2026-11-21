# Deployment Instructions — v2 Signal Upgrade

**Issue:** USO-469
**Target Server:** 10.10.10.100
**Estimated Time:** 30 minutes
**Risk Level:** Low (v2 runs alongside originals, different magic numbers)

---

## What This Deployment Does

1. **Kills 15 losing signals** — closes all open positions and removes EAs for signals that lost $31,274 combined
2. **Deploys 5 v2 winning signals** — upgraded versions with M5 monitoring layer for better entries/exits
3. **Keeps original 5 winners running** — v2 runs alongside them with separate magic numbers

### Signal Summary

| Action | Signals | Magic Range | Combined P&L |
|--------|---------|-------------|--------------|
| **KILL** | P14, P15, P16, P21, P22, P23, P30, P31, P32, P33, P34, P36, P38, P44, P46 | 208014–208046 | -$31,274 |
| **KEEP** | P1, P43, P45, P47, P48 | 208001–208048 | +$3,395 |
| **NEW v2** | P01_v2, P43_v2, P45_v2, P47_v2, P48_v2 | 209001–209048 | — |

---

## Pre-deployment Checklist

- [ ] Connect to 10.10.10.100 via Remote Desktop
- [ ] Verify MT5 is running and connected to Pepperstone
- [ ] Note current account balance: $__________
- [ ] Take screenshot of current open positions (Trade tab)
- [ ] Take screenshot of current chart layout showing all active EAs
- [ ] Verify algo trading is enabled (green play button in toolbar)
- [ ] Confirm you have the deployment package folder ready on the server

---

## Phase 1: Kill Losing Signals (10 minutes)

### Step 1.1 — Copy the KillLosers script

Copy from the deployment package to MT5:

```
Source:  mt5_eas\Scripts\KillLosers.mq5
Target:  [MT5 Data Folder]\MQL5\Scripts\KillLosers.mq5
```

To find the MT5 Data Folder: in MT5, go to **File → Open Data Folder**.

### Step 1.2 — Compile the script

1. Open **MetaEditor** (press F4 in MT5, or click the MetaEditor icon)
2. In MetaEditor: **File → Open** → navigate to `MQL5\Scripts\KillLosers.mq5`
3. Press **F7** to compile
4. Verify the **Errors** tab shows **0 errors, 0 warnings**
5. Close MetaEditor, return to MT5

### Step 1.3 — Dry run first

1. In MT5 Navigator panel (Ctrl+N), expand **Scripts**
2. Drag `KillLosers` onto any chart
3. In the dialog, go to the **Inputs** tab
4. Verify **InpDryRun = true** (this is the default)
5. Click **OK**
6. Open the **Experts** tab at the bottom of MT5
7. Review the output — it lists every position/order that WOULD be closed
8. Note the count and unrealized P&L

### Step 1.4 — Execute the kill (LIVE)

1. Drag `KillLosers` onto any chart again
2. In the **Inputs** tab, set **InpDryRun = false**
3. Click **OK**
4. Watch the **Experts** tab for confirmation messages
5. Verify the summary line: `Positions closed: X (failed: 0)`

**If any positions fail to close:** wait 30 seconds and run the script again. Market may have been between ticks.

### Step 1.5 — Remove losing EAs from charts

The losing signals were running as EAs on charts. After killing positions, remove those EA instances:

For each chart running a losing signal:
1. Right-click the chart → **Expert Advisors → Remove**
2. Confirm removal

**Losing signals to look for in chart comments/EA names:**

| Signal | Magic | Symbol | What to look for |
|--------|-------|--------|-----------------|
| P14 | 208014 | GBPCAD | EA comment containing "P14" |
| P15 | 208015 | XAUUSD | EA comment containing "P15" |
| P16 | 208016 | USDCAD | EA comment containing "P16" |
| P21 | 208021 | XAUUSD | EA comment containing "P21" |
| P22 | 208022 | XAUUSD | EA comment containing "P22" |
| P23 | 208023 | XAUUSD | EA comment containing "P23" |
| P30 | 208030 | EURGBP | EA comment containing "P30" |
| P31 | 208031 | AUDNZD | EA comment containing "P31" |
| P32 | 208032 | GBPCAD | EA comment containing "P32" |
| P33 | 208033 | EURCHF | EA comment containing "P33" |
| P34 | 208034 | EURGBP | EA comment containing "P34" |
| P36 | 208036 | EURGBP | EA comment containing "P36" |
| P38 | 208038 | EURCHF | EA comment containing "P38" |
| P44 | 208044 | USDJPY | EA comment containing "P44" |
| P46 | 208046 | USDCAD | EA comment containing "P46" |

### Step 1.6 — Verify kill complete

1. Open the **Trade** tab — no positions with the killed magic numbers should remain
2. Open the **History** tab — confirm the closes appear in recent history
3. Take screenshot for audit trail

---

## Phase 2: Deploy v2 Signals (15 minutes)

### Step 2.1 — Copy framework file

```
Source:  mt5_eas\Include\M5MonitorFramework.mqh
Target:  [MT5 Data Folder]\MQL5\Include\M5MonitorFramework.mqh
```

This file extends the existing `NewsTraderFramework.mqh` (which should already be in Include/).

### Step 2.2 — Copy v2 EA files

Create the V2 folder and copy the EAs:

```
Target folder: [MT5 Data Folder]\MQL5\Experts\V2\
```

Copy these files:

```
Source:  mt5_eas\Experts\P01_v2.mq5
Target:  [MT5 Data Folder]\MQL5\Experts\V2\P01_v2.mq5

Source:  mt5_eas\Experts\P43_v2.mq5
Target:  [MT5 Data Folder]\MQL5\Experts\V2\P43_v2.mq5

Source:  mt5_eas\Experts\P45_v2.mq5
Target:  [MT5 Data Folder]\MQL5\Experts\V2\P45_v2.mq5

Source:  mt5_eas\Experts\P47_v2.mq5
Target:  [MT5 Data Folder]\MQL5\Experts\V2\P47_v2.mq5

Source:  mt5_eas\Experts\P48_v2.mq5
Target:  [MT5 Data Folder]\MQL5\Experts\V2\P48_v2.mq5
```

### Step 2.3 — Compile all v2 EAs

1. Open **MetaEditor** (F4)
2. Open each `.mq5` file from `MQL5\Experts\V2\`
3. Press **F7** to compile each one
4. Verify **0 errors** for each. Warnings about "unused variables" are OK.
5. All 5 `.ex5` files should appear in the V2 folder

### Step 2.4 — Open 5 new M5 charts

For each v2 signal, open a new chart:

| # | Symbol | How to Open |
|---|--------|------------|
| 1 | EURUSD | Market Watch → right-click EURUSD → Chart Window |
| 2 | EURUSD | Market Watch → right-click EURUSD → Chart Window |
| 3 | NZDUSD | Market Watch → right-click NZDUSD → Chart Window |
| 4 | AUDUSD | Market Watch → right-click AUDUSD → Chart Window |
| 5 | GBPUSD | Market Watch → right-click GBPUSD → Chart Window |

**Set ALL 5 charts to M5 timeframe** (click the "M5" button in the toolbar for each chart).

### Step 2.5 — Attach v2 EAs to charts

Attach each EA from Navigator → Expert Advisors → V2:

| Chart # | Symbol | EA to Attach | Magic Number | Verify Input |
|---------|--------|-------------|--------------|--------------|
| 1 | EURUSD M5 | P01_v2 | 209001 | InpNotionalEUR = 1000 |
| 2 | EURUSD M5 | P43_v2 | 209043 | InpNotionalEUR = 1000 |
| 3 | NZDUSD M5 | P45_v2 | 209045 | InpNotionalEUR = 1000 |
| 4 | AUDUSD M5 | P47_v2 | 209047 | InpNotionalEUR = 1000 |
| 5 | GBPUSD M5 | P48_v2 | 209048 | InpNotionalEUR = 1000 |

For each EA:
1. Drag from Navigator onto the correct chart
2. **Common tab:** check "Allow algo trading"
3. **Inputs tab:** verify magic number and notional are correct
4. Click **OK**
5. Verify the **smiley face** icon appears in the top-right corner of the chart

**Note:** P01_v2 and P43_v2 both trade EURUSD but on separate charts with different magic numbers. This is correct — they have different entry logic.

### Step 2.6 — Verify v2 initialization

Open the **Experts** tab and look for initialization messages from each v2 EA:

```
[P01_v2] v2 initialized: symbol=EURUSD, spread_max=2.0x, confirm=6 bars, reversal=3 candles
[P43_v2] v2 initialized: symbol=EURUSD, spread_max=2.0x, confirm=6 bars, reversal=3 candles
[P45_v2] v2 initialized: symbol=NZDUSD, spread_max=2.0x, confirm=6 bars, reversal=3 candles
[P47_v2] v2 initialized: symbol=AUDUSD, spread_max=2.0x, confirm=6 bars, reversal=3 candles
[P48_v2] v2 initialized: symbol=GBPUSD, spread_max=2.0x, confirm=6 bars, reversal=3 candles
```

If any EA shows `INIT_FAILED`, check the error message and verify the framework file was copied correctly.

---

## Phase 3: Final Verification (5 minutes)

### Verify active EAs

After deployment, you should have:

| Category | EA | Magic | Symbol | Chart TF |
|----------|-----|-------|--------|----------|
| Original winner | P1 config | 208001 | EURUSD | (original TF) |
| Original winner | P43 config | 208043 | EURUSD | (original TF) |
| Original winner | P45 config | 208045 | NZDUSD | (original TF) |
| Original winner | P47 config | 208047 | AUDUSD | (original TF) |
| Original winner | P48 config | 208048 | GBPUSD | (original TF) |
| **NEW v2** | P01_v2_EURUSD | 209001 | EURUSD | M5 |
| **NEW v2** | P43_v2_EURUSD | 209043 | EURUSD | M5 |
| **NEW v2** | P45_v2_NZDUSD | 209045 | NZDUSD | M5 |
| **NEW v2** | P47_v2_AUDUSD | 209047 | AUDUSD | M5 |
| **NEW v2** | P48_v2_GBPUSD | 209048 | GBPUSD | M5 |

**Total: 10 active EAs** (5 original winners + 5 v2 upgrades)

### Verification checklist

- [ ] No positions open from killed signals (magic 208014–208046)
- [ ] All 5 original winners still running (magic 208001, 208043, 208045, 208047, 208048)
- [ ] All 5 v2 EAs show smiley face icon
- [ ] Experts log shows 5 successful v2 initializations
- [ ] No error messages in Experts log
- [ ] Algo trading is enabled (green play button)

### Save the chart profile

1. **File → Profiles → Save As**
2. Name: `V2_Deployed_20261121`
3. Click OK

This saves the chart layout so it can be restored if MT5 restarts.

---

## Rollback Plan

If anything goes wrong with v2 deployment:

### Quick rollback (remove v2 only)
1. For each v2 chart: right-click → Expert Advisors → Remove
2. Close the 5 v2 charts
3. Original winners continue running unaffected

### Full rollback (restore losing signals)
This is NOT recommended — the losing signals lost $31,274 over 49 days. But if needed:
1. Re-attach the original EAs to charts with the original magic numbers
2. The KillLosers script only closes positions; it does not modify EA files

### v2 uses separate magic numbers (209xxx)
v2 positions and original positions (208xxx) never interfere:
- v2 EAs only manage positions with their own magic number
- Original EAs only manage positions with their own magic number
- Portfolio manager handles cross-signal risk at the account level

---

## Emergency Contacts

- **CTO (agent):** Check Paperclip issue USO-469 for technical context
- **MT5 support:** Pepperstone broker support chat/phone

---

## Post-deployment Monitoring

After deployment, monitor for the first 24 hours:

1. Check Experts log every few hours for errors
2. Verify v2 signals are generating trades on the expected symbols
3. Compare v2 vs original signal timing — v2 should enter slightly later (M5 confirmation delay)
4. If v2 trades cluster at the same time as originals, this is expected — both react to the same events
