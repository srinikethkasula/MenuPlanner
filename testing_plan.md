# Menu Planner Executable Testing Plan

This document outlines the detailed step-by-step testing plan to validate the packaging, portability, and user interface refinements of the compiled **MenuPlanner** single-file executable.

---

## 📦 Distribution & Terminal Download (For Employees)

Employees can download the latest compiled `MenuPlanner.exe` executable directly to their Windows Desktop using the terminal:

### PowerShell (Default on Windows)
```powershell
Invoke-WebRequest -Uri "https://github.com/<YOUR_USERNAME>/<YOUR_REPO>/releases/latest/download/MenuPlanner.exe" -OutFile "$HOME\Desktop\MenuPlanner.exe"
```

### CMD (Command Prompt)
```cmd
curl -L -o "%USERPROFILE%\Desktop\MenuPlanner.exe" "https://github.com/<YOUR_USERNAME>/<YOUR_REPO>/releases/latest/download/MenuPlanner.exe"
```

---

## 🎛️ Test Environment & Preparation

Before beginning execution of the test suites, prepare a clean testing environment to ensure first-run behavior works as expected.

### Step 1: Force Close Existing Runs
Close any active or frozen runs of the Menu Planner.
```powershell
Stop-Process -Name "MenuPlanner" -Force -ErrorAction SilentlyContinue
```

### Step 2: Clean the AppData Directory
To simulate a "first launch" on a client machine, temporarily rename your active user directory:
1. Press `Win + R`, type `%APPDATA%`, and hit `Enter`.
2. Locate the folder named `MenuPlanner`.
3. Rename it to `MenuPlanner_Backup` (or delete it if you don't have custom plans you wish to keep).

---

## 🧪 Test Suites

### Suite 1: First-Run Initialization & Seeding
**Objective:** Verify that a clean launch extracts all assets, databases, and seeds 194 image resources correctly.

| Step | Action | Expected Result | Pass/Fail |
|---|---|---|---|
| 1 | Double-click the compiled `dist/MenuPlanner.exe` to launch. | A premium gold/slate gourmet cover dome splash screen appears immediately. | |
| 2 | Wait for the main window to open. | The main interface launches successfully in dark mode, showing "Chathradhari Caterers" brand titles. | |
| 3 | Press `Win + R`, navigate to `%APPDATA%/MenuPlanner`. | A `data` directory and `export` directory are created. | |
| 4 | Open `%APPDATA%/MenuPlanner/data` | Contains the `menu_planner.db` database and a `dish_images` folder. | |
| 5 | Open `dish_images` inside the `data` folder. | Contains **exactly 194** dish seed photos (e.g. `Chicken Handi.jpg`, `Egg Lajawab.jpg`). | |

---

### Suite 2: Dialog Layouts & Fixed Sizes
**Objective:** Verify all modal dialog boxes open at fixed, non-resizable window sizes and show no squeezed layout fields.

#### Test 2.1: Add Custom Dish Dialog
1. Click the **+ Dish** (or **＋ Add Custom Dish**) button.
2. **Verification:**
   - [ ] The dialog window title is **"Add Custom Dish"**.
   - [ ] The window size is locked at `520x700` pixels. Try resizing the borders with your cursor—they should not stretch.
   - [ ] The **Nutrition Info (optional)** fields (Calories, Protein, Carbs, Fat, Fiber) are spaced out nicely, with no overlapping borders or squeezed input lines.
   - [ ] The bottom-right button is present, fully visible, and labeled **`✓  Save Dish`**.

#### Test 2.2: Edit Dish Dialog
1. Double-click any dish card in the left library dock (e.g., *Kombdi Rassa*).
2. **Verification:**
   - [ ] The dialog window title is **"Edit Dish"**.
   - [ ] The name field is prefilled.
   - [ ] The bottom-right button is present and labeled **`✓  Save Dish`**.
   - [ ] All inputs and labels are fully readable and do not overlap.

#### Test 2.3: Settings Dialog
1. Go to **File -> Settings** (or click **Settings** button in main header).
2. **Verification:**
   - [ ] Dialog opens in a fixed `520x420` size (non-resizable).
   - [ ] Inputs for Company/Canteen name and closing images are laid out cleanly.
   - [ ] Bottom contains cancel and **`✓  Save Settings`** buttons.

#### Test 2.4: Image Manager Dialog
1. Go to **Dishes -> Image Manager**.
2. **Verification:**
   - [ ] Dialog opens in a fixed `760x560` size.
   - [ ] Table headers ("Dish Name", "Image Path", "✓") fit without horizontal scrollbars.
   - [ ] Double-clicking a row correctly opens the file browser.

---

### Suite 3: Database & Local Image Writable Operations
**Objective:** Verify that adding, modifying, or deleting data works seamlessly in the AppData directory.

| Step | Action | Expected Result | Pass/Fail |
|---|---|---|---|
| 1 | Open **Add Custom Dish**, enter a custom name "Test Biryani", click **Browse** under Image, select any image from your computer, and click **✓ Save Dish**. | - The new card is added to the left dock under the "Custom" category.<br>- The image file is copied, renamed, and converted to `.jpg` inside `%APPDATA%/MenuPlanner/data/dish_images/Test_Biryani.jpg`. | |
| 2 | Double-click the "Test Biryani" card to edit, change the category to "Breakfast", change calories to "400 kcal", and click **✓ Save Dish**. | - The card updates in the dock.<br>- Re-opening the card shows the edited values preserved. | |
| 3 | Drag the card "Test Biryani" to a slot on Monday (e.g. Spl.Veg). | The dish is successfully planning into Monday. | |
| 4 | Right-click the "Test Biryani" card in the dock, click **Delete Dish**, and confirm. | - The dish is deleted from the dock.<br>- The slot assignment on Monday is cleared automatically. | |

---

### Suite 4: Slide Preview & PowerPoint/Excel Exports
**Objective:** Verify the unified slides render correctly and export without file compilation errors.

1. **Slide Preview Generation:**
   - [ ] Set up a few dishes in the middle planner grid (drag dishes to different days).
   - [ ] Look at the right **Slide Preview** pane.
   - [ ] Click through the day buttons (MON, TUE, etc.) to verify that the slides render live with custom backgrounds, category colored badges, and food photographs matching the assignments.
2. **PowerPoint & Excel Exports:**
   - [ ] Click the blue **Export** button in the header bar.
   - [ ] In the fixed `540x520` Export Dialog, select Monday-Friday, check both PowerPoint and Excel boxes, select a save folder (e.g., your Desktop), and click **Export Now**.
   - [ ] **Verification:**
     - The progress bars fill, and green checks appear.
     - Go to your Desktop: verify that Excel files (`MenuPlanner_Week_...xlsx`) and PowerPoint slides (`MenuPlanner_MON.pptx`, etc.) are generated.
     - Open the Excel file: verify the layout grid is filled.
     - Open the PowerPoint slides: verify that backgrounds, logos, and custom text show up.
3. **Dynamic Slide Category Labeling Verification:**
   - [ ] Drag an item to the **FRUIT** section (e.g., `Daily Fruit` to the `Daily Fruit` slot) and check the slide preview. Verify the slide header displays **`"FRUIT LUNCH"`**.
   - [ ] Drag a sweet item (e.g., `Moong Dal Payasam` or `Kesar Kulfi`) to a main course lunch slot (e.g., `SPL.VEG.`). Look at the slide preview. Verify the category displays **`"DESSERT"`** (rather than `"LUNCH"`).
   - [ ] Drag `Omelet` to the `EGG` slot in the `ADDITIONAL` section. Look at the slide preview. Verify the category displays **`"BREAKFAST"`**.
   - [ ] Export the PowerPoint slides and open the generated `.pptx` files to verify that these exact category labels match the slides.

---

## 🧳 Suite 5: Portability & Crash Recovery

#### Test 5.1: Portable Executable execution
1. Copy the compiled `MenuPlanner.exe` from `dist/` to a completely different directory (e.g. your Desktop, or a USB drive).
2. Launch it from that new location.
3. **Verification:**
   - [ ] The app boots instantly and reads the existing `%APPDATA%/MenuPlanner/data/menu_planner.db`.
   - [ ] Any custom dishes or planning details created during previous steps are fully preserved.

#### Test 5.2: Crash Recovery Detection
1. While the app is running, open Windows Task Manager and end the `MenuPlanner` process (or force close it).
2. Relaunch `MenuPlanner.exe`.
3. **Verification:**
   - [ ] On startup, the app detects the unclean shutdown.
   - [ ] A dialog message appears saying: *"The application was not closed cleanly last time. Your data has been recovered from the database."*
   - [ ] The database remains uncorrupted and rolls back transactions safely.
