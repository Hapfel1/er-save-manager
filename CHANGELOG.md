# 📜 ER Save Manager - Release History

> A comprehensive changelog for the Elden Ring Save Manager application.
> All notable changes to this project are documented here.

## 📦 Release 2.0.2
**Released:** October 05, 2026


### 📦 Dependencies

- General: Bump taiki-e/install-action ([5c52e54](https://github.com/Hapfel1/er-save-manager/commit/5c52e5480489b66cee684eb2baed13048feeed80))


---
## 📦 Release 2.0.1
**Released:** October 02, 2026


### 🔧 Bug Fixes

- ER: Reworked Inventory Loadouts Function ([8ec24f9](https://github.com/Hapfel1/er-save-manager/commit/8ec24f97a347295a426f58a90465bcea8c0703a1))

- General: Keep gaitem handles and inventory counters in game range ([55ca4cf](https://github.com/Hapfel1/er-save-manager/commit/55ca4cfb10fc4bed94c09c8c23082bd43d829df0))

- General: Stop external-change dialog firing on the tool's own writes ([8161c2b](https://github.com/Hapfel1/er-save-manager/commit/8161c2bf2ac9d0b3172af4ac2a1699ba9be4b509))

- General: Keep pickers, visual editors and tabs in sync in all games ([8ca4bc7](https://github.com/Hapfel1/er-save-manager/commit/8ca4bc7379e7ff86640b534cfe4320e21b1d18f7))

- General: Smooth DS2 bonfire view updates, Ctrl+A select all on Linux ([5c989ad](https://github.com/Hapfel1/er-save-manager/commit/5c989ad41d934d818e3e3fd3f86c8539a5271371))

- General: Run Auto-Find search off the UI thread ([0b7514e](https://github.com/Hapfel1/er-save-manager/commit/0b7514e5255e7269dac56b10a328e2dcfe31b8a8))

- General: Stop external-change notifications from stacking ([ca3c573](https://github.com/Hapfel1/er-save-manager/commit/ca3c5732b298c5d80a86a11fb09b4b5da61caff3))


### 🎨 User Interface

- General: Reworked and unified color palette ([c8f8214](https://github.com/Hapfel1/er-save-manager/commit/c8f8214fc56d8c04ae2aa90712b83f7e40ecdc9a))


### ⚡ Performance Improvements

- General: Speed up batch item adds ([100ac01](https://github.com/Hapfel1/er-save-manager/commit/100ac017dd6f13b491ae99232c38a83904af6c39))

- General: Build category grids in batches ([614f8b3](https://github.com/Hapfel1/er-save-manager/commit/614f8b35bacf2058fadaafb64c0fb9d0bdeb7928))

- General: Faster grid selection, debounced search, staged tab builds ([be42ec9](https://github.com/Hapfel1/er-save-manager/commit/be42ec9a791a45635c48a99e61972313a18774cf))


---
## 📦 Release 2.0.0
**Released:** October 01, 2026


### ✨ New Features

- ER: Revive Shadow of the Erdtree NPCs ([379cf30](https://github.com/Hapfel1/er-save-manager/commit/379cf305b3c34eed98e1ae76f86fd0e184300b8e))

- DS3: Added Visual Item Picker and Visual Inventory Editor ([8c075cd](https://github.com/Hapfel1/er-save-manager/commit/8c075cdc8b0bfb477acf6c0915858a70334e1604))

- DS3: Added Boss Respawning functionality ([1ee0559](https://github.com/Hapfel1/er-save-manager/commit/1ee0559b87c1bbcd09e26e39725b93da0308b0cf))

- DS3: Added Bonfire Editor ([4fb23de](https://github.com/Hapfel1/er-save-manager/commit/4fb23de64b09ab0243acbc14a1f6d7236eb9567f))

- DS3: Added NPC Respawner ([86436f5](https://github.com/Hapfel1/er-save-manager/commit/86436f525e8404ccebdf86e7456fb6bb05f25f04))

- DS3: Added Gesture Editor ([a93216c](https://github.com/Hapfel1/er-save-manager/commit/a93216c16cfb1c254cea43b7affb564191cbb730))

- DS2: Added import feature for builds from soulsplanner.com ([3881d33](https://github.com/Hapfel1/er-save-manager/commit/3881d333997aaa021f315e1f2c97a1297523bc40))

- DS2: Equip an imported Souls Planner build's loadout ([0c4a9f4](https://github.com/Hapfel1/er-save-manager/commit/0c4a9f4493e3b15d136e662e392c2ca808ac7c7f))

- DS2: Attune an imported Souls Planner build's spells ([70f511d](https://github.com/Hapfel1/er-save-manager/commit/70f511d494e78fd6fc8985a2a565504605398ce1))

- DSR: Added Visual Item Picker and Visual Inventory Editor ([7b980c3](https://github.com/Hapfel1/er-save-manager/commit/7b980c304eeb071b64b4012de126ba9166b0e448))

- DSR: Light and unlight bonfires ([4e00af3](https://github.com/Hapfel1/er-save-manager/commit/4e00af3d2ce5fd8c743d5ea48527594b3501d171))

- NR: Add loadouts tab, relic copy-to-spawn and JSON import/export ([b153385](https://github.com/Hapfel1/er-save-manager/commit/b153385595c5e69eb234faed31e63c8b5492427f))

- General: Delete several backups at once ([51c242f](https://github.com/Hapfel1/er-save-manager/commit/51c242fb7d033285bb51d411d0f0cd3ad5087b9b))

- General: Version 2.0 ([ec3dbf2](https://github.com/Hapfel1/er-save-manager/commit/ec3dbf2fc08cade9a24e66dd9fa063546de23412)) ⚠️ **BREAKING CHANGE**


### 🔧 Bug Fixes

- DS3: Reworked item spawning ([f55e7e9](https://github.com/Hapfel1/er-save-manager/commit/f55e7e9639a0540072f404854a2e4b9aebdc2e33))

- DS3: Improved Item Database and added full validation for Vanilla/Convergence/Cinders ([40b9496](https://github.com/Hapfel1/er-save-manager/commit/40b9496d97b6d1836f95858d33e28e1e966c57db))

- DS3: Fixed errors with DS3 Save File Parsing ([c1d8b4c](https://github.com/Hapfel1/er-save-manager/commit/c1d8b4c3b6125ccc2cb4d5406e03769293edef3a))

- DS3: Map gestures to table rows and light one state flag per bonfire ([6960d56](https://github.com/Hapfel1/er-save-manager/commit/6960d569aaed949a775ded768260d4eff26f2d3d))

- DS3: Keep list action buttons visible in short windows ([04314f1](https://github.com/Hapfel1/er-save-manager/commit/04314f1929eae6a4eb286c8d3f6fc9a3af539a61))

- DS3: Add Seamless Co-op goods and limit Estus Flasks to one ([987abed](https://github.com/Hapfel1/er-save-manager/commit/987abedb32347e39c59745002dda7ff24e3d0d07))

- DS3: Clear the map death bit when reviving NPCs ([5f72f18](https://github.com/Hapfel1/er-save-manager/commit/5f72f18c3bc0b15b89c6bee5527abb2f14f4497a))

- DS2: Store non-key goods in the main inventory, flag cut content unsafe ([981e777](https://github.com/Hapfel1/er-save-manager/commit/981e7771fa19f4782aa3f4c721d118f953de639a))

- DS2: Validate soulsplanner links by parsed host ([e653ca7](https://github.com/Hapfel1/er-save-manager/commit/e653ca73d7cec6fb80bf913f6a80e8a9bbf23db8))

- DS2: Keep equipped items from being removed or stored ([0e7d7ce](https://github.com/Hapfel1/er-save-manager/commit/0e7d7ce127f7b56d78e7f3e0da4247dcfd01e723))

- DS2: Give boss souls and Seamless Co-op items their icons ([d21d9cf](https://github.com/Hapfel1/er-save-manager/commit/d21d9cf1bca25ccf6dd592b85e37a6c2d12ef434))

- DSR: Use the verified event flag layout; re-enable boss and NPC edits ([fee937d](https://github.com/Hapfel1/er-save-manager/commit/fee937d870f34d6fdf30351ad86788db2dd8c8e9))

- DSR: Fixed event flag layouts ([e5b1896](https://github.com/Hapfel1/er-save-manager/commit/e5b1896ccb3b9bb487cf8fd952284651e2d9cf31))

- NR: Keep slot size fixed and offsets fresh on relic spawn/remove ([d9da1c3](https://github.com/Hapfel1/er-save-manager/commit/d9da1c320ab5b335ebd1d2a3a2b09b4070a6ca26))

- NR: Parse loadout chunk from its header and harden relic ops ([db5052d](https://github.com/Hapfel1/er-save-manager/commit/db5052d45cef41b7d740246f88cc1f1a7bcbfdd7))

- NR: Align preset array and parse modded or over-capacity loadouts ([3a63823](https://github.com/Hapfel1/er-save-manager/commit/3a63823a56cc01f9e27d22532c3ab29c481ba2e4))

- General: Strip AppImage library paths when opening folders on Linux ([76d914e](https://github.com/Hapfel1/er-save-manager/commit/76d914e9ac58e351e6a7475ee1d1ce6430054734))

- General: Strip AppImage library paths from remaining external launches ([ce39d57](https://github.com/Hapfel1/er-save-manager/commit/ce39d57f2ba7f4545ee20befe666c7993f8ef0c4))

- General: Replace emoji in widget text on Linux ([cdc9476](https://github.com/Hapfel1/er-save-manager/commit/cdc9476d290508e9bae2a2fab26f04341f933390))


### 🎨 User Interface

- DS3: Always show the spawn infusion and grey out inapplicable fields ([77396b5](https://github.com/Hapfel1/er-save-manager/commit/77396b53826cbf880c389368f1c2f3b485faabe4))

- DS2: Multi-select in the visual picker and inventory ([e0c80a7](https://github.com/Hapfel1/er-save-manager/commit/e0c80a7f3493114008e023effc3cc97afb3aca2c))

- DS2: Add an Add All Shown button to the visual item picker ([2ec0323](https://github.com/Hapfel1/er-save-manager/commit/2ec0323f1f4554e2c80b290bc699757553a16185))


### 📖 Documentation

- DSR: Document bonfire lighting ([93bd40a](https://github.com/Hapfel1/er-save-manager/commit/93bd40a5f5baf04521e1436b1fb248113189e7ae))

- General: Updated docs ([baa1b30](https://github.com/Hapfel1/er-save-manager/commit/baa1b302a51826a2d5d995f2d0e0254ae26f8d91))

- General: Update README and DS3 guide for the DS3, DS2 and Nightreign changes ([3516586](https://github.com/Hapfel1/er-save-manager/commit/35165866b62210da2e70113896a0a46d77fbf7ff))

- General: Add Dark Souls II user guide ([f93e43b](https://github.com/Hapfel1/er-save-manager/commit/f93e43be53d964894d66f32b9a546e5656fd6156))


### ⚡ Performance Improvements

- DS3: Cache gaitem positions and scan lists in one pass ([64a8259](https://github.com/Hapfel1/er-save-manager/commit/64a8259c6f760ddcaeb80617d8cba9f25a0ba348))

- General: Improved Tab Loading times ([ad7b590](https://github.com/Hapfel1/er-save-manager/commit/ad7b590492a433b571dfe7e6def6ef870b8d2d75))

- General: Store DS3 and DSR item lists as CSV ([84e3580](https://github.com/Hapfel1/er-save-manager/commit/84e3580be79bb8c14a85d678c66e29ed2d2da732))


### ♻️ Code Refactoring

- General: Load ER flag and location tables from JSON ([e1bcea1](https://github.com/Hapfel1/er-save-manager/commit/e1bcea1997e36ad8bf3cc162270d836c0321d668))


---
## 📦 Release 1.12.2
**Released:** September 29, 2026


### 🔧 Bug Fixes

- DS2: Support the item box ([7a121ea](https://github.com/Hapfel1/er-save-manager/commit/7a121eaa60912990dc7abb3448fb271b963c7722))

- General: Close scrollable dropdowns on a click outside them ([88881b5](https://github.com/Hapfel1/er-save-manager/commit/88881b5a9176e527ca5a74ef18bde2a8837e13d2))

- General: Hide deleted characters from ER slot dropdowns ([dac5f7b](https://github.com/Hapfel1/er-save-manager/commit/dac5f7b3d3c7a452615e6c58331663cea4361745))


### 🎨 User Interface

- ER: Use scrollable dropdowns for event flag and grace filters ([32e1918](https://github.com/Hapfel1/er-save-manager/commit/32e19182963fb9baa2fd52d09692592406a67f4b))

- DS2: Added Torch Duration editor ([6769a67](https://github.com/Hapfel1/er-save-manager/commit/6769a67fd8c47f455e3de6320d10824ced866d78))

- General: Show the save file name first in the save selector ([0553406](https://github.com/Hapfel1/er-save-manager/commit/05534069c8b5f3131adfc8983d19e2d56069e4ad))


---
## 📦 Release 1.12.1
**Released:** September 29, 2026


### 🔧 Bug Fixes

- DS2: Made spells quantity fixed and made it possible to spawn multiple copies of the same spell ([751f613](https://github.com/Hapfel1/er-save-manager/commit/751f613d3aafbd1ce2a4dbddfaa65bdbfa8782dd))

- DS2: Readd forgotten npc kill records ([28e36fd](https://github.com/Hapfel1/er-save-manager/commit/28e36fd67b59546959638c3896b8953bb576c8aa))

- DS2: Show named characters that were treated as never created ([7390e3a](https://github.com/Hapfel1/er-save-manager/commit/7390e3a049a18a4fe0fe84d69d47c92f5de29430))


### 🎨 User Interface

- DS2: Show infusion icons and infused weapon names ([4c8bb2c](https://github.com/Hapfel1/er-save-manager/commit/4c8bb2c6e00cbe32c2beea390006a86415b6daa5))

- DS2: Add a visual bonfire viewer with bonfire pictures ([1084754](https://github.com/Hapfel1/er-save-manager/commit/10847547cb6b9ef2f942b3d472485b1a42be7742))


### 📖 Documentation

- General: Complete credits and fix license and feature listings ([c9504a4](https://github.com/Hapfel1/er-save-manager/commit/c9504a45aa4d22e051750008472489b2abf616c4))

- General: Correct SteamID patcher coverage ([b8f8459](https://github.com/Hapfel1/er-save-manager/commit/b8f845919333d2f5749ae62b1a56e151160c535f))


### ⚡ Performance Improvements

- General: Render the flag list in a Treeview ([157262a](https://github.com/Hapfel1/er-save-manager/commit/157262a46d188af7b066f7eb06d419ce39167b9c))


---
## 📦 Release 1.12.0
**Released:** September 29, 2026


### ✨ New Features

- DS2: Regulation-backed item limits, bulk add and upgrade editing ([5422614](https://github.com/Hapfel1/er-save-manager/commit/542261438b462206f3b6233e2b5d4d1c5c4b20fb))

- DS2: Weapon infusion editing, weapon copies and multi-select remove ([a067b81](https://github.com/Hapfel1/er-save-manager/commit/a067b8175b3dcb0107a931b0027a3a5026136351))

- DS2: Tell pre-character-creation slots apart from never-created ones ([b0643a2](https://github.com/Hapfel1/er-save-manager/commit/b0643a20b756e0b8b48b360fa3aeb087ef03488e))

- DS2: Added Bonfire Editing: Activating/Deactivating bonfires and setting bonfire ascetic level ([5651ac1](https://github.com/Hapfel1/er-save-manager/commit/5651ac1c0ea7edd207a833cdc564e790bf629595))

- DS2: Added NPC Reviver ([5a0cd59](https://github.com/Hapfel1/er-save-manager/commit/5a0cd59eda68e2e77a1f0d1271c5a8efe2eb8995))

- General: feat(ds2): add scroll containers to editor stats and inventory tabs ([6084d4e](https://github.com/Hapfel1/er-save-manager/commit/6084d4e0aec648a2a1a142cee80f4f0c0ed91d6a))

- General: Feat(ui): add configurable default game
Add a default_game setting used to pick the game on startup. A button next to the game dropdown shows whether the selected game is the default or sets it. ([af91f04](https://github.com/Hapfel1/er-save-manager/commit/af91f04b8e02380e989bb43ca1fc0c99c1cfcf74))


### 🔧 Bug Fixes

- DS2: Validated and tested all NPC entries ([13ea43f](https://github.com/Hapfel1/er-save-manager/commit/13ea43fe1af90f262a6d46be397218a8c6118eed))

- DS2: Stack goods onto existing quantity instead of overwriting it ([a0f4f42](https://github.com/Hapfel1/er-save-manager/commit/a0f4f42dc2dc9ae858676cdcb4e0a480d0caf477))

- General: Fix(settings): keep auto-backup save path when enabling toggle:
The toggle handler captured the game config before opening the save chooser, then wrote it back afterwards, overwriting the path the chooser had just stored. Re-read the config after the chooser and revert the checkbox when no valid path is chosen. ([323aa6a](https://github.com/Hapfel1/er-save-manager/commit/323aa6ac2af02edebc581f6e543cafd4441ee4fc))

- General: fix(ds2): correct intelligence/faith/adaptability offsets and 1-based NG+ ([7bb7e02](https://github.com/Hapfel1/er-save-manager/commit/7bb7e022a2f2a083b731d78fa0f6de271b4d1b48))

- General: fix(ds2): validate item spawns, fixed soul vessel crashing the game ([7552b5c](https://github.com/Hapfel1/er-save-manager/commit/7552b5c85852cea6f34ed6ac6e186a8c085f477c))

- General: fix(ui): run SteamID refresh off the UI thread for DS2/DS3 loads and fix toast stack cleanup ([e163e29](https://github.com/Hapfel1/er-save-manager/commit/e163e2964ee70c917efda786ebf5324aaca74306))

- General: Fix(ui): center windows correctly under UI/DPI scaling
CTk scales the width and height passed to geometry() but not the x/y offset, so every dialog that centered itself from the unscaled size opened right and below its target at scales above 100%. Add center_window() to ui/utils.py, which computes the offset from the scaled size, centers on screen or over a parent, and caps oversized windows. Use it for the main window and all dialogs, and make the duplicated _center_over helpers delegate to it. Windows that had no positioning now open centered over their parent. Fix the map window sizing itself as a screen fraction in unscaled units. ([1e4ed1d](https://github.com/Hapfel1/er-save-manager/commit/1e4ed1df9dc369c935c86b8c4ac20539f52f0b5e))


### 🎨 User Interface

- DS2: Grey out inapplicable inventory controls and edit several rows, add tooltips, more userfriendly UI ([1f9d999](https://github.com/Hapfel1/er-save-manager/commit/1f9d99923ee036c60fcd02dbe0cf36692c9bfd6a))

- DS2: Added Visual Item Picker and Visual Inventory Editor ([7bf854c](https://github.com/Hapfel1/er-save-manager/commit/7bf854c4ffeaffe590f7450e04374822667f8199))


### ⚡ Performance Improvements

- General: perf(steamid): use C-speed scans to avoid multi-second UI stalls on save load ([40cfb86](https://github.com/Hapfel1/er-save-manager/commit/40cfb86c4aacbdfcd6bd04a62889439f892bbbd1))

- General: Use C-speed scans in SteamID detection to avoid multi-second UI stalls on save load ([081c246](https://github.com/Hapfel1/er-save-manager/commit/081c2462bec745497b824da28797cb25a65c39b2))


### 📦 Dependencies

- General: Bump the github-actions group with 2 updates ([17e313f](https://github.com/Hapfel1/er-save-manager/commit/17e313f7a56d1987431d5f8d23b81661acf6360d))


---
## 📦 Release 1.11.0
**Released:** September 23, 2026


### ✨ New Features

- ER: Add Sites of Grace dialog to the event flags tab ([1dc2b67](https://github.com/Hapfel1/er-save-manager/commit/1dc2b67ff3e45258bf83bb8fce0d16a142bbe67b))

- ER: Add show item IDs and custom ID item adder dev options ([17a1321](https://github.com/Hapfel1/er-save-manager/commit/17a13216b8a757916563ddee920e5299af989811))

- General: Added Weapon-Batch-Upgrading to the Visual Inventory Editor: ([a3d30c5](https://github.com/Hapfel1/er-save-manager/commit/a3d30c53982fd6a76b692f457e50a8d89f60c031))

- General: Feat: added Convergence Mod sites of grace to EVENT_FLAGS and
FLAGS_BY_CATEGORY ([1cb7879](https://github.com/Hapfel1/er-save-manager/commit/1cb7879edcc96923bffc9d28fa258a69ee93b175))

- General: Add is_convergence helper ([d43d49b](https://github.com/Hapfel1/er-save-manager/commit/d43d49b1961e6bd0d419863c8fefba08ee05debd))

- General: Add Max button to batch weapon upgrade dialog ([baed03d](https://github.com/Hapfel1/er-save-manager/commit/baed03d1099f95562a4181d03e2eae089509be94))


### 🔧 Bug Fixes

- DS2: Clipped add button, seamless items, garbled slot names ([2a3ca45](https://github.com/Hapfel1/er-save-manager/commit/2a3ca45725e5e75f1b599fe7adf8e7f9de3758d2))

- DS2: Correct item IDs and stop writing bogus unk_1 on new items ([e70f38e](https://github.com/Hapfel1/er-save-manager/commit/e70f38e6f10e5e3e29b55c8b6537f4084c79e5ed))

- General: Fix: get_flag_name now works like before the addition of EventFlagInfo
again ([ca07cbd](https://github.com/Hapfel1/er-save-manager/commit/ca07cbdc34115a366a458bc053796ac015a653ac))

- General: Remove duplicate id from wrong category ([bb3e4ec](https://github.com/Hapfel1/er-save-manager/commit/bb3e4ec94f49599b8b3491e9514161eadeac8895))

- General: Hide convergence-only subcategories and flags on non-convergence saves ([bdebe35](https://github.com/Hapfel1/er-save-manager/commit/bdebe3518dd203ad7f2067fe8c25e84caa5de5c9))

- General: Correct Forbidden Lands spelling in grace category ([ddc7af3](https://github.com/Hapfel1/er-save-manager/commit/ddc7af3cc01907a161186831618d22e6ad52eb72))

- General: Refresh subcategory dropdown filter when a save loads ([1c97a9d](https://github.com/Hapfel1/er-save-manager/commit/1c97a9dcdaa3747d839ca5fffcbf28eab57f3824))

- General: Stale flag render and stale filters in event flags tab ([4117065](https://github.com/Hapfel1/er-save-manager/commit/41170652936d9089e70b6f5fef3b0b03888a19a9))


### 🎨 User Interface

- General: Hide Convergence Mod exclusive flags from non Convergence Mod saves ([d67cb2d](https://github.com/Hapfel1/er-save-manager/commit/d67cb2da805db0798c73758a8c2140e9ec0b7d9a))


### 📦 Dependencies

- General: Bump the github-actions group with 2 updates ([c618e33](https://github.com/Hapfel1/er-save-manager/commit/c618e33a2bfc484086aee8b5675e748001e3247f))


---
## 📦 Release 1.10.3
**Released:** September 15, 2026


### 🔧 Bug Fixes

- General: Combo dropdown popup misplaced at (0,0) on Windows ([0193f15](https://github.com/Hapfel1/er-save-manager/commit/0193f15cc8363f9be506deb44d66fdd7bceae344))

- General: Add separate fix for Tarnished pack entry flag ([0a17bb9](https://github.com/Hapfel1/er-save-manager/commit/0a17bb9a0973422313df2c73fa79db5d016a18fe))

- General: Resolve Convergence class list gaps ([ef59ce8](https://github.com/Hapfel1/er-save-manager/commit/ef59ce8f9e16ac0ad9d4ef2df071c8322e4908ff))

- General: Remove unneeded comparison and update outdated comment ([f6a1304](https://github.com/Hapfel1/er-save-manager/commit/f6a1304b09c1fb95a0adc3cce99a03f24241d044))


### 🎨 User Interface

- General: Replace category dropdown with scrollable popup ([d4630e9](https://github.com/Hapfel1/er-save-manager/commit/d4630e9b840618469966a9faef4a2a1da522e9d3))

- General: Replace CTkComboBox native dropdown with scrollable popup ([72b0768](https://github.com/Hapfel1/er-save-manager/commit/72b07687f934a48a6c1010a6e3aec9fc8e43e92e))


### 📖 Documentation

- General: Docs:add missing technical doc sections between BloodStain and Event
Flags ([a59a64f](https://github.com/Hapfel1/er-save-manager/commit/a59a64f5ca3bb8ddd71cd0e09562806fe80ef2d1))

- General: Docs:add missing technical doc sections between Event Flags and
PlayerCoordinates ([2290b43](https://github.com/Hapfel1/er-save-manager/commit/2290b43356522aaae88fd0b8b01c277baa0a8887))

- General: Docs(technical): correct wrong types for MenuSaveLoad, wrong offset for
FieldArea etc. and correct byte count for `event_flags_terminator` after
Event Flags ([620897b](https://github.com/Hapfel1/er-save-manager/commit/620897bf85ba1f196cea2379aeef0134da2e9373))

- General: Fix offsets for MenuSaveLoad and trim newlines ([7335f62](https://github.com/Hapfel1/er-save-manager/commit/7335f6246211f8e7ad69341706b481bcab8c0887))

- General: Fix offsets for all new sections, where applicable ([21ef932](https://github.com/Hapfel1/er-save-manager/commit/21ef9327afd1777e887c47ff0ab64c47f55aa067))


---
## 📦 Release 1.10.2
**Released:** September 11, 2026


### 🔧 Bug Fixes

- General: Match .cnv anywhere in filename, not just as suffix ([d9c627d](https://github.com/Hapfel1/er-save-manager/commit/d9c627db648dbe9c4411a717c365a43359edd51c))

- General: Batch remove items by category in visual inventory ([5e78ca6](https://github.com/Hapfel1/er-save-manager/commit/5e78ca6eca8a908a80b9646cda332b7259aae7ba))

- General: Added missing icons ([8481dd3](https://github.com/Hapfel1/er-save-manager/commit/8481dd3a6d3d6aee0d3a5ee0743a8a719368567f))


### 🎨 User Interface

- General: Add save/game version reference table ([8dbca69](https://github.com/Hapfel1/er-save-manager/commit/8dbca69a8c77e4c58e5cbec9bf725d2e42434a1d))


### 📖 Documentation

- General: Update Mistakes in Save-File-Structure Docs, added GaItem Description ([f22c53f](https://github.com/Hapfel1/er-save-manager/commit/f22c53fdf1b55838922adbfca13d81b12cbb566c))


### 📦 Dependencies

- General: Bump taiki-e/install-action in the github-actions group ([0d704e1](https://github.com/Hapfel1/er-save-manager/commit/0d704e13f878fbcff6a2b838dfa1a3e846301bef))


### Ds2

- General: Hide never-created slots from save inspector list ([cf14269](https://github.com/Hapfel1/er-save-manager/commit/cf14269ea07c132229cccb19c550631c9e98b3b3))


---
## 📦 Release 1.10.1
**Released:** September 02, 2026


### 🔧 Bug Fixes

- General: Add save/game version mismatch fix ([d3323fa](https://github.com/Hapfel1/er-save-manager/commit/d3323fa4eb2c16f7d6366f59fa431a74bfbc4802))


### 📦 Dependencies

- General: Bump urllib3 from 2.6.3 to 2.7.0 ([6107be0](https://github.com/Hapfel1/er-save-manager/commit/6107be003ebb1eaf59e8b640b4244f939fdf9f16))


---
## 📦 Release 1.10.0
**Released:** September 01, 2026


### ✨ New Features

- General: Add Tarnished Pack DLC items and DLC-gated content ([6b7d265](https://github.com/Hapfel1/er-save-manager/commit/6b7d2658e9cd210431df1a2b85adbfb3791713f4))


### 🔧 Bug Fixes

- General: Added Tarnished Pack Starting Classes ([4d60fde](https://github.com/Hapfel1/er-save-manager/commit/4d60fdeeb95aef0f0113511bf4a32d6e1c2f7e7c))

- General: Prevent EAC warning from silently cancelling save load ([d3a50ea](https://github.com/Hapfel1/er-save-manager/commit/d3a50ead9f85353425d8f0f8cea7a5330d18c254))


### 📦 Dependencies

- General: Bump taiki-e/install-action in the github-actions group ([c915105](https://github.com/Hapfel1/er-save-manager/commit/c915105839ef22e55b3dec85fcd9ea92246a6ec5))

- General: Bump taiki-e/install-action in the github-actions group ([86f89a6](https://github.com/Hapfel1/er-save-manager/commit/86f89a671cf88f26e5c10825cdf932cf3794b05b))


---
## 📦 Release 1.9.1
**Released:** August 17, 2026


### 🔧 Bug Fixes

- General: Block save writes while the game is running ([0e93040](https://github.com/Hapfel1/er-save-manager/commit/0e9304046650c54107dd59cbeedd947cabe9cf9e))

- General: Allow visual inventory and icon browser open together ([68e95d4](https://github.com/Hapfel1/er-save-manager/commit/68e95d4fcefcebd33a18980e6311e35b753db201))


### 🎨 User Interface

- General: Added option to lock/favorite backups which will never get purged/deleted ([a78e5c3](https://github.com/Hapfel1/er-save-manager/commit/a78e5c3a11fc795f7b34f3d2993225c8974fed3d))

- General: Added label/reason input field when creating manual backup, falls back to "manual" when left empty ([190cff4](https://github.com/Hapfel1/er-save-manager/commit/190cff486e23d619623bc3864f530c914c252b1c))

- General: Add sort control to the inventory editor list ([70d76c3](https://github.com/Hapfel1/er-save-manager/commit/70d76c33c0a206f9e67dd76109b8ba863bd4c31e))


### 📦 Dependencies

- General: Bump the github-actions group with 2 updates ([3f845dd](https://github.com/Hapfel1/er-save-manager/commit/3f845dd7524cb821f8f04b9fa6d7bc3709e4b216))

- General: Bump pyjwt from 2.10.1 to 2.13.0 ([3bbcc7a](https://github.com/Hapfel1/er-save-manager/commit/3bbcc7adf2b9816631d8a474b4785aa0e05a3a70))


---
## 📦 Release 1.9.0
**Released:** August 11, 2026


### ✨ New Features

- General: Add interval-based auto-backup while game is running ([41685ed](https://github.com/Hapfel1/er-save-manager/commit/41685ed25f99eadf2df5ed2d3f3ce25810f93ebf))

- General: CodeQL advanced workflow (actions + python) ([43903a5](https://github.com/Hapfel1/er-save-manager/commit/43903a50bd8eb92ec07f441edbb319d6240c0ef5))


### 🔧 Bug Fixes

- General: Use correct empty-slot sentinel when writing gesture array ([0ef4a2b](https://github.com/Hapfel1/er-save-manager/commit/0ef4a2bd1d4d583bc80a854924e78ddf6f191c5d))

- General: Added missed item, Lantern ([03195e2](https://github.com/Hapfel1/er-save-manager/commit/03195e282e6b8fc8b3e3e31d0f379006ce593c5c))

- General: Add missed items for Convergence ([89a74de](https://github.com/Hapfel1/er-save-manager/commit/89a74de5d9ee30c54e1c8341d6360334688368f0))

- General: Scope gaitem lookup to target inventory location ([06fcf16](https://github.com/Hapfel1/er-save-manager/commit/06fcf1608d6370a66169215245edfec6c74a484e))

- General: Exclude orphaned gaitem_map entries from weapon/armor picker ([f851bae](https://github.com/Hapfel1/er-save-manager/commit/f851baeed1cccbb1ed1c10129e91bef48f012fa3))


### 📦 Dependencies

- General: Bump the github-actions group with 2 updates ([337dbfa](https://github.com/Hapfel1/er-save-manager/commit/337dbfa8ac1a9a31797f834bcb284986ee6dd07c))

- General: Bump taiki-e/install-action in the github-actions group ([5d52ae4](https://github.com/Hapfel1/er-save-manager/commit/5d52ae498310dd51c2256a754e1247a8d2becc4f))

- General: Bump pillow from 12.1.0 to 12.3.0 ([763c374](https://github.com/Hapfel1/er-save-manager/commit/763c3745e7773d09545a8f500c53ea6e3da4357d))

- General: Bump cryptography from 46.0.3 to 50.0.0 ([6f4373d](https://github.com/Hapfel1/er-save-manager/commit/6f4373d8f474af0da7cd077045390ca98aa40392))


---
## 📦 Release 1.8.0
**Released:** July 30, 2026


### ✨ New Features

- DS2: Back up before every write, sortable inventory columns, update steamid docs ([7e04d2f](https://github.com/Hapfel1/er-save-manager/commit/7e04d2f568379e4cebd7c9bc622b683cca669f76))

- General: Fix for the "Missing Romina" bug ([3727d86](https://github.com/Hapfel1/er-save-manager/commit/3727d86718eaa0a1c76af9a97c6e078f93670b29))

- General: Ruins of Unte golem fix for Seamless Co-op ([0c6e0d1](https://github.com/Hapfel1/er-save-manager/commit/0c6e0d1e9d314bd1b80d2682dedbc613b5307087))

- General: Erdtree state detection ([793a2dc](https://github.com/Hapfel1/er-save-manager/commit/793a2dc0a1b4d2d16058aa40b45d629edf42a3d9))

- General: Add character management for DSR, DS3, and Nightreign ([16a7262](https://github.com/Hapfel1/er-save-manager/commit/16a7262dd189dcfbb692875c108bae29bfe6841c))

- General: Add Support for DS2 Save File Editing ([3590874](https://github.com/Hapfel1/er-save-manager/commit/3590874778484e9ed93b9e7dea7ddee29d3ae699))


### 🔧 Bug Fixes

- DS2: More UI fixes ([4426585](https://github.com/Hapfel1/er-save-manager/commit/44265855c229a0de0d82bb20b30b60fbbdf00e2b))

- General: Fixed Typo and added flag 3001 which triggers NG on teleport to Roundtable Hold ([a38b256](https://github.com/Hapfel1/er-save-manager/commit/a38b2560e6beb981c08647d2ee4a14f3c19857ea))

- General: Sync qty/upgrade/location vars before batch add ([13e4ddc](https://github.com/Hapfel1/er-save-manager/commit/13e4ddc41ae732a10b79924e7014923344ce9ed0))

- General: Use atomic writes in DS3, DSR, NR parsers and steamid patchers ([c010f83](https://github.com/Hapfel1/er-save-manager/commit/c010f83ef2ceaf44825dfe68b7c869294563d745))

- General: Kill correct process when force-terminating non-ER games ([3f32cd8](https://github.com/Hapfel1/er-save-manager/commit/3f32cd852ac8211571ed62da003ac3799db4c147))

- General: Fixed Poisoned Hand being documented as smithing stone weapon, added unique armor set version to Convergence Armor ([8306a20](https://github.com/Hapfel1/er-save-manager/commit/8306a20fa77044e9c6a7096ae70c959cb7e7553a))

- General: Commit max backups on enter/focus-out instead of every keystroke ([7f826b7](https://github.com/Hapfel1/er-save-manager/commit/7f826b76ff69e2f550634817a4dda3d9a9b70aec))

- General: Use native file dialogs for export/import/transfer ([0ab47a5](https://github.com/Hapfel1/er-save-manager/commit/0ab47a5684f1690f0c531077c117a36274f2d049))

- General: Add autofind + manual browse to transfer target picker ([2ea9233](https://github.com/Hapfel1/er-save-manager/commit/2ea9233da2550697bde9849c1cd615f79979a44d))

- General: Add auto-backup toast instead of popup message and add setting to disable it ([98941fd](https://github.com/Hapfel1/er-save-manager/commit/98941fd0c972d6186a20adee30c517b7a0b11888))

- General: Set all affinity unlock flags for whetblades ([f67e889](https://github.com/Hapfel1/er-save-manager/commit/f67e889417fcc6c79640e7de1fe14c64088339b4))

- General: Warn before lowering max backups prunes existing backups ([de8d835](https://github.com/Hapfel1/er-save-manager/commit/de8d835677518090b186bf3e7dfead09ed6ba216))


### 🎨 User Interface

- General: Add note about  stale load-screen summary after copy/transfer ([c00382c](https://github.com/Hapfel1/er-save-manager/commit/c00382c1ecd7d98c78b0f1c1f0e5c4937c3e8713))


### 📖 Documentation

- General: Replace MIT with source-available license ([5ae4eb5](https://github.com/Hapfel1/er-save-manager/commit/5ae4eb598c002fbc2f8d28fa95fc52000c816f16))

- General: Update license link in readme ([830214d](https://github.com/Hapfel1/er-save-manager/commit/830214dff784b2c9a9ecd5ff8d9d264260ac80a3))


### ♻️ Code Refactoring

- General: Resolve convergence items via item_database instead of missing hex files ([d650262](https://github.com/Hapfel1/er-save-manager/commit/d650262f4ba9fd1105f979215715c81acb01d1db))


### 📦 Dependencies

- General: Bump the github-actions group with 3 updates ([fd3fe9e](https://github.com/Hapfel1/er-save-manager/commit/fd3fe9eeb1e2107739c5a1254952dcbe8977d6b0))


---
## 📦 Release 1.7.1
**Released:** July 22, 2026


### 🔧 Bug Fixes

- General: Fixed Browse Button not working on Linux with new native file explorer implementation ([59270c0](https://github.com/Hapfel1/er-save-manager/commit/59270c0158e4df34a802aba9f4de715f3491adce))

- General: Fixed missing Icons and duplicate Item Names ([aa0d664](https://github.com/Hapfel1/er-save-manager/commit/aa0d664159c048ad4f3daec4e5e838a916c9eed0))

- General: Add Native File PIcker for Lnux to "Save Icon" button in Visual Item Picker ([b0d78e8](https://github.com/Hapfel1/er-save-manager/commit/b0d78e8e5bfa1d9d3b5a3ec9de2be8c7c201ab69))


### 🎨 User Interface

- General: Fixed Padding for Icons ([34614b2](https://github.com/Hapfel1/er-save-manager/commit/34614b2fc8c26e1765b58059be20d773db71bf58))


---
## 📦 Release 1.7.0
**Released:** July 21, 2026


### ✨ New Features

- General: Add kill functionality mirroring respawn ([8bd48ff](https://github.com/Hapfel1/er-save-manager/commit/8bd48ff118fe9ef34ea62fbde415c6bba8d2df78))

- General: Add structural integrity scan module ([9543a7a](https://github.com/Hapfel1/er-save-manager/commit/9543a7a70565f25d920e915fe183e2ef55d0e6f6))

- General: Add share-code import/export for appearance presets and inventory loadouts ([2c4d259](https://github.com/Hapfel1/er-save-manager/commit/2c4d259abca4cf1da5131ef6ee106c0ac982dc65))

- General: Complete equipment editor - persistence fix, loadouts, visual picker ([1303cdc](https://github.com/Hapfel1/er-save-manager/commit/1303cdc49de00c9d8df17cca3353e027c37d0586))


### 🔧 Bug Fixes

- DSR: Use fixed offset for NPC/event flag anchor instead of pattern search ([0793494](https://github.com/Hapfel1/er-save-manager/commit/07934947ec69ad2ef20fb3b97ebbdc7731556690))

- General: Add missing CHECKSUM_SIZE class constant ([bffbe8b](https://github.com/Hapfel1/er-save-manager/commit/bffbe8beb150d7b9e5de154ca4a0ca43f3012eeb))

- General: Add Blessed Blue Dew Talisman Convergence variant to Convergence Talismans which reuses the Cerulean Seed Talisman's ID still with its old name in Params ([8cbd2d9](https://github.com/Hapfel1/er-save-manager/commit/8cbd2d9f3148e7a5a90f5a73637f9624b2d8a86f))

- General: Remove empty scrollable_frame widget and fix test exit code masking ([09b667d](https://github.com/Hapfel1/er-save-manager/commit/09b667d37009bd8b0330763a8ac7a61240a9890d))

- General: Include OpenSSL DLLs in root to prevent PATH conflicts under zip_include_packages ([d9c08e7](https://github.com/Hapfel1/er-save-manager/commit/d9c08e77668380f85d669d0dd4e7418ff2f52eb2))

- General: Atomic save writes, unique backup names, preserve rebuild_slot tail data ([51f938d](https://github.com/Hapfel1/er-save-manager/commit/51f938deee42cdd05e97738c1f9e237c95e8da07))

- General: Use fixed 600 cap for ammo storage quantity ([ec655b3](https://github.com/Hapfel1/er-save-manager/commit/ec655b3fb61dc74b80dbfc1ce3cf16cdd25e7b60))

- General: Added more Item event flag linking ([f72491b](https://github.com/Hapfel1/er-save-manager/commit/f72491b8cf9b7fbcbf4ef2bbaa174e3aa46afa4b))

- General: Fixcharacter-info): remove non-functional fields from info editor

Remove extra talisman slots, spirit summon level, max crimson flask, and max cerulean flask fields from the character info editor UI, load, and apply logic. These fields had no in-game effect when edited directly. ([cf5bc66](https://github.com/Hapfel1/er-save-manager/commit/cf5bc66cad117b3bb6320dcd2baf6997b61f52f0))

- General: Fixed earlier byte discarding fix getting reverted ([8e443b1](https://github.com/Hapfel1/er-save-manager/commit/8e443b1a78b6375878b1d334ba14e36db2e17966))


### 🎨 User Interface

- NR: Show curse slot widgets for deep relics in editor ([3117279](https://github.com/Hapfel1/er-save-manager/commit/31172792002160479216a63a54535e4d14d8a962))

- General: Use native Linux file picker for all manual file browse dialogs ([3c3fc66](https://github.com/Hapfel1/er-save-manager/commit/3c3fc668a1f5356623dc5ade3a3c5a15ebb8505a))


### 📖 Documentation

- General: Fix fixer, character editor, event flags, world state, settings docs; add other-games guides ([081b472](https://github.com/Hapfel1/er-save-manager/commit/081b47205cc5757cb209ae7b580e301d617b8d24))


### 📦 Dependencies

- General: Bump the github-actions group with 2 updates ([a2d1bf4](https://github.com/Hapfel1/er-save-manager/commit/a2d1bf41ff429daa6b74380228f7005b47fcc981))

- General: Bump the github-actions group with 3 updates ([cdfa8bb](https://github.com/Hapfel1/er-save-manager/commit/cdfa8bba49c2d690d50c3d901ae796ddc6b27576))


---
## 📦 Release 1.6.2
**Released:** July 08, 2026


### 🔧 Bug Fixes

- General: Add missed Convergence Armor ([7451875](https://github.com/Hapfel1/er-save-manager/commit/7451875870c3330eea509a158fdecced7ac8f85a))

- General: Fallback to storage on held-full during add/batch/loadout ([c13299c](https://github.com/Hapfel1/er-save-manager/commit/c13299c652dbc8768cdfd17099a8722315720006))


### 📦 Dependencies

- General: Bump the github-actions group with 2 updates ([3f3e1f6](https://github.com/Hapfel1/er-save-manager/commit/3f3e1f6b16e706fa4508a7bcb5e6a82d15f6d378))


---
## 📦 Release 1.6.1
**Released:** July 03, 2026


### 🔧 Bug Fixes

- General: Exclude compiled extension packages from Windows zip ([aa1fea9](https://github.com/Hapfel1/er-save-manager/commit/aa1fea913c0b92f8dd27a6c467ada0ae399e5614))


---
## 📦 Release 1.6.0
**Released:** July 03, 2026


### ✨ New Features

- General: Add Elden Bling Auto Sliders JSON import ([7812ba0](https://github.com/Hapfel1/er-save-manager/commit/7812ba0ab8f6ef455e7554142191b01f7aeb79ef))


### 🔧 Bug Fixes

- General: Fall back to actual list when removing/setting quantity ([228c389](https://github.com/Hapfel1/er-save-manager/commit/228c389443c9580f5a6fcd93660c689e936f5253))

- General: Shift all downstream slot offsets on gaitem insert/remove ([7eb3b4d](https://github.com/Hapfel1/er-save-manager/commit/7eb3b4d7fb0d2958177466b22276d57198d4f185))


### Data

- General: Add missing convergence items, fix item names, update icons ([1516d4f](https://github.com/Hapfel1/er-save-manager/commit/1516d4f1fb23109d568897437983fd90b02e9c16))


---
## 📦 Release 1.5.2
**Released:** June 29, 2026


### 🔧 Bug Fixes

- General: Correct consumable stack location and convergence upgrade caps (#193) ([7504329](https://github.com/Hapfel1/er-save-manager/commit/75043296d8e82fe28b49024c36ff325f35d8539b))

- General: Correct inventory counter updates for key items in add/remove ([1a483e9](https://github.com/Hapfel1/er-save-manager/commit/1a483e953bcea59eec23eaccede503fc0f707527))

- General: Trigger auto-backup on every game launch, not once per session ([36741ff](https://github.com/Hapfel1/er-save-manager/commit/36741ff435c747854329ac28fd3752090feb3eef))

- General: Rename invasion regions to unlocked regions ([c0cd80d](https://github.com/Hapfel1/er-save-manager/commit/c0cd80d9fcc585f02078e5bf875c838f1c086d9c))

- General: Detect and repair corrupted inventory item counters in character details ([f9020be](https://github.com/Hapfel1/er-save-manager/commit/f9020be0bb3738874e222d76f55d0d881ce94ff7))

- General: Add Event Flag mapping for maps and ashes of war ([9bde103](https://github.com/Hapfel1/er-save-manager/commit/9bde103548005a28fe2756f747faa5c53a730df1))


### 🎨 User Interface

- General: Add Video Guide button for Ghost's video guide ([d25fa56](https://github.com/Hapfel1/er-save-manager/commit/d25fa560229ed02b75d2b04846e3abececbb01c2))


### 📦 Dependencies

- General: Bump the github-actions group with 2 updates ([ff228e4](https://github.com/Hapfel1/er-save-manager/commit/ff228e4e5175a48e9e5c1055019ce48a82c4bba0))


### Data

- General: Migrate icon storage from zip to sqlite, fix nexus mods quarantine ([439f948](https://github.com/Hapfel1/er-save-manager/commit/439f9485eec4921eaf26ef0e49b954b69f836e36))


---
## 📦 Release 1.5.1
**Released:** June 23, 2026


### 🔧 Bug Fixes

- General: Update player_game_data_offset after gaitem shift and bump mm level on weapon spawn ([fc434b1](https://github.com/Hapfel1/er-save-manager/commit/fc434b1ff803312c8f58afc7c30feaafe8a6378b))

- General: Auto-adjust matchmaking level on weapon removal, remove manual set button ([a4e25a8](https://github.com/Hapfel1/er-save-manager/commit/a4e25a8936bf26c6284885af8773c29a5b7dd4d2))

- General: Added missed Convergence Item, Warding Remnant ([217e7a6](https://github.com/Hapfel1/er-save-manager/commit/217e7a619add1d766d78d0d4283e1ca55b4300b3))

- General: Add boss status dialog, fix bell bearing NG+ flags, fix search debounce (closes #189) ([2ed2d88](https://github.com/Hapfel1/er-save-manager/commit/2ed2d8830c181d51c2b2df5a3a52202f8129b280))

- General: Prevent integer overflow from corrupted acquisition indices ([c6470f8](https://github.com/Hapfel1/er-save-manager/commit/c6470f8d323e34e084b5d2b147b99489fb650a9c))

- General: Adjust UI spacing and resolve loadout file path ([6fe6676](https://github.com/Hapfel1/er-save-manager/commit/6fe6676894eabe43d1cb668b8fe7e650275849c3))


### 🎨 User Interface

- General: Made CSNetMan.bin replace button show permanently ([14700af](https://github.com/Hapfel1/er-save-manager/commit/14700affc1ef25f904b9ce13af8d0fa2aed3764b))

- General: Made Message about CsNetMan more clear ([09b9267](https://github.com/Hapfel1/er-save-manager/commit/09b92670ab4cc9f5479dd4d32371285c1e3fe954))

- General: Add Debug warped face button ([04bba00](https://github.com/Hapfel1/er-save-manager/commit/04bba002c301ce2cf5a2855fdc4b7541ab33464e))

- General: Add loadout manager, batch spawning, and smart stacking ([77b09b6](https://github.com/Hapfel1/er-save-manager/commit/77b09b65dd5e9c118d2318f9519492363dbc4888))

- General: Replace warped face button with slider dialog for secondary face deformation ([bcb73dd](https://github.com/Hapfel1/er-save-manager/commit/bcb73dd2530aaa8ffd8142c0b1ecf3b5909108c3))


### ♻️ Code Refactoring

- General: Remove CSNetMan replace button toggle setting ([c6be1d3](https://github.com/Hapfel1/er-save-manager/commit/c6be1d34d70774a411829909774e1f7dc9baf979))


### 📦 Dependencies

- General: Bump the github-actions group with 3 updates ([249e547](https://github.com/Hapfel1/er-save-manager/commit/249e54759b33461be16013e184e3f71f31410fe9))


### 🧹 Maintenance

- General: Migrate nexusmods upload action to v1.0.0-beta.8 ([a51f7dc](https://github.com/Hapfel1/er-save-manager/commit/a51f7dc8fd3372978d3668e7e073f1aec33d805d))


---
## 📦 Release 1.5.0
**Released:** June 18, 2026


### ✨ New Features

- NR: Add Nightreign save editor ([9606d27](https://github.com/Hapfel1/er-save-manager/commit/9606d27fe98bee7f1d502643c8f34d7efa9d829b))

- General: Add 3.0 update support ([c0152c7](https://github.com/Hapfel1/er-save-manager/commit/c0152c7f03b2c84a503c06f6b69323cfbcc007df))


### 🔧 Bug Fixes

- NR: Fix relics tab layout in fixed-height window ([38a778c](https://github.com/Hapfel1/er-save-manager/commit/38a778ce85639916bc0ac3ade9cc1db17fe79de7))

- General: Removed cut content cookbooks ([d68ad4a](https://github.com/Hapfel1/er-save-manager/commit/d68ad4abceb6d720ccacc5c2381ac04c6b4e102f))

- General: Cookbook/whetblade event flags and display fixes ([5d3eed4](https://github.com/Hapfel1/er-save-manager/commit/5d3eed4e371594dfa54491dc06c05965d0eb7496))

- General: Expand _KEY_ITEM_BASE_IDS with all confirmed key item categories ([1d23cec](https://github.com/Hapfel1/er-save-manager/commit/1d23cec7abdc0270e22ff10b5ebb5a4d3e719fb2))

- General: Remove cut content and fix item names across goods CSVs ([2527929](https://github.com/Hapfel1/er-save-manager/commit/25279298f5e0589548e5ad7f24fff9180068a7e0))

- General: Add containers and upgrade items to _KEY_ITEM_BASE_IDS ([8abb756](https://github.com/Hapfel1/er-save-manager/commit/8abb7568182972ca0890136260f7ef352e748f22))

- General: Add Dragon Heart and Lost Ashes of War to _KEY_ITEM_BASE_IDS ([c226241](https://github.com/Hapfel1/er-save-manager/commit/c226241c94ff3b0e6e78759d1aeb85f80eac1c52))

- General: Remove two cut content items ([ade100e](https://github.com/Hapfel1/er-save-manager/commit/ade100e8cd05c5046f4ff58afa94994b1eebb2d4))


### 🎨 User Interface

- General: Ui: Fixed Icons being the same for modified variants of certain Items:
Lord of Blood's Favor
Unalloyed Gold Needle
Miniature Ranni
Academy Glintstone Key
Larval Tear ([53d9306](https://github.com/Hapfel1/er-save-manager/commit/53d9306fa7eae668e7f8dd9ab070f5be31aa512c))

- General: Replace pruning warning with pre-deletion CTk dialog ([780027e](https://github.com/Hapfel1/er-save-manager/commit/780027e24430b42bdef109d04d7c5e0ca2e2df72))


### 📦 Dependencies

- General: Bump taiki-e/install-action in the github-actions group ([f5f7167](https://github.com/Hapfel1/er-save-manager/commit/f5f716791de66b40387994b29f9260f2d61294c0))


---
## 📦 Release 1.4.1
**Released:** June 09, 2026


### 🔧 Bug Fixes

- DS3: Fix weapon spawn ([be6beba](https://github.com/Hapfel1/er-save-manager/commit/be6bebabaa5153a1a215afcfe4e96b7dcfe97602))

- DSR: Correct body type encoding, NPC alive/dead offset handling ([a3556b9](https://github.com/Hapfel1/er-save-manager/commit/a3556b95d9bcb17f67d6d843c4a4ed15fab7d210))

- General: Ashes Name Resolution, Allow Duplicate Talismans, Fix Melee filter exlcuding infused weapons in visual inventory ([4db254e](https://github.com/Hapfel1/er-save-manager/commit/4db254e63b285407e7edfa229d8eb19f875acdc5))

- General: Removed "No Presets" warning as this is not needed anymore and is possible now ([0e50b2f](https://github.com/Hapfel1/er-save-manager/commit/0e50b2fc8f90d761e1f4b7d064211c270bde9087))

- General: Fix incorrect starting class ID assignment #169 ([aaf2c67](https://github.com/Hapfel1/er-save-manager/commit/aaf2c67b330e044c5f879765cdd189162a17e56d))

- General: Enforce class stat minimums in stats editor, notify on archetype change ([23921e9](https://github.com/Hapfel1/er-save-manager/commit/23921e917cd8ed2a893ca04f246428acd9b9ef20))

- General: Correct wrong IDs for 8 ashes in Ashes.csv and DLCAshes.csv #170 ([2cd8152](https://github.com/Hapfel1/er-save-manager/commit/2cd815200fcaad6b0379957107794dc12683c42c))

- General: Match gems in gaitem map by base_id via handle prefix ([83f1810](https://github.com/Hapfel1/er-save-manager/commit/83f1810cb7f2953f524ec8a9b989db56c2c52fb6))

- General: Hide PS button for non-ER games, fix item gib DS3 nav, restore SteamID tab position on PC save reloadfix: hide PS button for non-ER games, fix item gib DS3 nav, restore SteamID tab position on PC save reload ([cf2f811](https://github.com/Hapfel1/er-save-manager/commit/cf2f811dc6eb111d0078eb1df52234023c20d5f2))

- General: Mirror gaitem handle second byte from save; add held→storage fallback ([5c0e147](https://github.com/Hapfel1/er-save-manager/commit/5c0e1478e4ce7da873d96c2474f318bd4fbe6649))

- General: Redo Item DB by getting data from Params ([8ca9edf](https://github.com/Hapfel1/er-save-manager/commit/8ca9edfdba9f3aa55a4ad466922dbe7a66f12772))

- General: Match gem gaitem by base_id or full_item_id ([e4b1a97](https://github.com/Hapfel1/er-save-manager/commit/e4b1a97f15fdac97da5c55e953bca1da992ef745))

- General: Accept more formats in the appearance tab JSON import ([63b82db](https://github.com/Hapfel1/er-save-manager/commit/63b82db5f5aaf2c30b33b8d844e3de1b1766e9b5))

- General: Potential PS fix for spawning weapons ([be98eb3](https://github.com/Hapfel1/er-save-manager/commit/be98eb337bf177fad64fe84ead15ad28fa0f3c24))

- General: Read second byte from first gaitem entry and reuse it for all spawned handle ([a3ff305](https://github.com/Hapfel1/er-save-manager/commit/a3ff3057ec493882f042e649565b934119b5387a))

- General: Default UI scale to 100% instead of Auto ([bc76ee9](https://github.com/Hapfel1/er-save-manager/commit/bc76ee9540c142c7e4b24cd7b47606dd0b8099d5))

- General: Lazy-load preset thumbnails in background threads ([778d164](https://github.com/Hapfel1/er-save-manager/commit/778d1645d49a5261308c8b1b57f1bfde000f4505))


### 🎨 User Interface

- General: Added Display Scale Setting ([07d394d](https://github.com/Hapfel1/er-save-manager/commit/07d394d5b6bd2a89e4dd1b9f7f716fc412b47da8))

- General: Add 104 NPC appearance presets to the preset browser ([9664509](https://github.com/Hapfel1/er-save-manager/commit/9664509bfacce1fe257793c2c871d1c35ec7e697))


### 📦 Dependencies

- General: Bump the github-actions group with 3 updates ([4aa7609](https://github.com/Hapfel1/er-save-manager/commit/4aa7609d0ea920b7ad2ce027d37323e643dd9395))


---
## 📦 Release 1.4.0
**Released:** June 04, 2026


### ✨ New Features

- ER: Added PlayStation Save File Reading and Editing ([5cc96a9](https://github.com/Hapfel1/er-save-manager/commit/5cc96a949c388081f935c1befb078740d035f034))

- DS3: Add DS3 save file editing ([90b1830](https://github.com/Hapfel1/er-save-manager/commit/90b1830d235844369d4c020ca7990f78554aa582))

- DS3: Add Item Spawning ([4495fea](https://github.com/Hapfel1/er-save-manager/commit/4495fea46ccdaa032852dd2c59969fb9e6f930c1))

- DS3: Add DS3 save file editor module ([1c18773](https://github.com/Hapfel1/er-save-manager/commit/1c18773290054fb3a41f3c33e906611961344c91))


### 🔧 Bug Fixes

- DSR: Correct event flag base offset, add level recalc, flag lookup tab ([0733060](https://github.com/Hapfel1/er-save-manager/commit/07330607a06803985a7ba6236e4bc6c42b6e8f1d))

- General: Added probing to find correct inventory size ([fb74414](https://github.com/Hapfel1/er-save-manager/commit/fb74414ae89c5157ab05a40ae5dd3aee38efd96e))

- General: Preserve global array header when writing to preset slot 0 ([4bfa53a](https://github.com/Hapfel1/er-save-manager/commit/4bfa53a6cbdb726ea95c0ecee3b79e664ae1ba70))

- General: Added mising Convergence Item, Putrid Key ([79d276d](https://github.com/Hapfel1/er-save-manager/commit/79d276d9ae6cac5d178168197005b2f9d1e260bc))

- General: Route key items to key_items[] in inventory ops ([89c6576](https://github.com/Hapfel1/er-save-manager/commit/89c65768e7d8785a62dc0b649c10db67c724047b))

- General: Skip checksum prefix on PS saves for all slot writes ([ace141d](https://github.com/Hapfel1/er-save-manager/commit/ace141d04c19b960f8b69681322cf2ef0e7da59c))


### 🎨 User Interface

- General: Redid character transferring between files flow to make it more user friendly ([08a9649](https://github.com/Hapfel1/er-save-manager/commit/08a964973bbb70aae74a232edbf86e2854374d6d))

- General: Add info about quest steps that stay applied even after fully resetting quest progress ([4855469](https://github.com/Hapfel1/er-save-manager/commit/4855469724289a3c029a5ceb3f7bbe1299a3db63))

- General: Fix scroll bar bug in Icon Browser ([0ba6589](https://github.com/Hapfel1/er-save-manager/commit/0ba65890345260872f7cdec86d1da11e2f23a7cf))

- General: Rewrite info text to adjust for Switch and Playstation saves ([0eb0c01](https://github.com/Hapfel1/er-save-manager/commit/0eb0c013e770ca65ec2db50f5dfe8311fa851e64))


### 📦 Dependencies

- General: Bump the github-actions group with 2 updates ([3b3747f](https://github.com/Hapfel1/er-save-manager/commit/3b3747f529a391a56742fd3df45202c4076319dd))


---
## 📦 Release 1.3.2
**Released:** May 29, 2026


### 🔧 Bug Fixes

- DSR: Added missed SeamlessCoop Item (Crimson Blossom) ([6f85f1b](https://github.com/Hapfel1/er-save-manager/commit/6f85f1b3c46bf2d83b5615508281a071f3c994fb))

- General: Fixed some convergence weapons having affinity options when they should not have them ([9e77aaa](https://github.com/Hapfel1/er-save-manager/commit/9e77aaa2d874f64836206a69d1582dc60fb72b4c))

- General: Added missing Attribute level validation ([cadf1a6](https://github.com/Hapfel1/er-save-manager/commit/cadf1a6911f3dfc88d2d873feb05e6dd4b7334fd))


### 🎨 User Interface

- General: Added SeamlessCoop Items for DSR ([bc3bc3b](https://github.com/Hapfel1/er-save-manager/commit/bc3bc3bc7a225d95388997963aa8ca3718740ee9))

- General: Added setting to disable "Save File modified externally" warning ([cabe487](https://github.com/Hapfel1/er-save-manager/commit/cabe487278d6f2c1b7cf35ed16598c1f3aa47c06))

- General: Fixed Search Indexing Bug in Icon Browser ([1a86722](https://github.com/Hapfel1/er-save-manager/commit/1a867220d65588ba93c97c8c20ae4bf4669e2975))

- General: Remove unnecessary popup when editing stats and also instantly change the level total in CSProfileSummary when total level changes ([43e6a3b](https://github.com/Hapfel1/er-save-manager/commit/43e6a3b29220c05cda77a9cefc64e4cd33674485))


---
## 📦 Release 1.3.1
**Released:** May 26, 2026


### 🔧 Bug Fixes

- General: Added missed Convergence Items (Maps and Perfumer quest items) ([fe6a843](https://github.com/Hapfel1/er-save-manager/commit/fe6a84355359b1fa538b0d3f1c10587b5395b435))

- General: Fixed issue with interpreting int level making it unable to apply NG+7 ([1002d35](https://github.com/Hapfel1/er-save-manager/commit/1002d35da7cc05e08e7e7b899c9903d5ed166f6c))

- General: Fixed build issue ([68ac838](https://github.com/Hapfel1/er-save-manager/commit/68ac8387acfdc0e7b4f09ccc71bd0d3db7d8cbe8))

- General: Write CSNetMan.bin at net_man_offset - 4 ([c2f73e7](https://github.com/Hapfel1/er-save-manager/commit/c2f73e765ab075633fe08533892d1382dd78cdaf))

- General: Fully implemented Affinity/Gem Validation for Convergence Saves ([4a90b21](https://github.com/Hapfel1/er-save-manager/commit/4a90b2151adaebdea05600d8525db73e94dcba66))


### 🎨 User Interface

- General: Add .cnv to the browse option filter ([c860719](https://github.com/Hapfel1/er-save-manager/commit/c8607194afaadff94b8ce33db5cbd273ffe94fc1))

- General: Fixed "Save File has been modified externally" popping up after modifying the save file with the manager ([7cd52f2](https://github.com/Hapfel1/er-save-manager/commit/7cd52f2083c4ac3371fd3094c1cdd102d5be36f7))


### 📦 Dependencies

- General: Bump taiki-e/install-action in the github-actions group ([7c6dafc](https://github.com/Hapfel1/er-save-manager/commit/7c6dafcea0ff5149ca1637d03fab77fd61bddf26))


---
## 📦 Release 1.3.0
**Released:** May 22, 2026


### ✨ New Features

- General: Add DSR Save Editing: Stats Editor, Inventory Editor, NPC&Boss Revival, World State ([91bc158](https://github.com/Hapfel1/er-save-manager/commit/91bc158629cc4d25d81c28bbabeccc7be5cd1434))

- General: Added Summoning Pool Button to the event flags tab to disable and enable summoning pools ([9367dc9](https://github.com/Hapfel1/er-save-manager/commit/9367dc916094e801d45b0de3d51df9035c88a3c9))


### 🔧 Bug Fixes

- General: Removed cut magic ([a3b0218](https://github.com/Hapfel1/er-save-manager/commit/a3b0218273cf92edaea3165caa61b806840ab4c3))

- General: Added early return for a guard that caused a crash ([2686335](https://github.com/Hapfel1/er-save-manager/commit/2686335ae4d420f095b2e014714b67752492b302))


### 🎨 User Interface

- DSR: Improve DSR tabs ([0738dbe](https://github.com/Hapfel1/er-save-manager/commit/0738dbecb5cb509cc89c1dc14f59a9df7a3c30cf))

- General: Add new popup when a loaded save file gets modified externally ([f4291e9](https://github.com/Hapfel1/er-save-manager/commit/f4291e92d64edf8b9a254cf6b3e6ab372279e403))

- General: Add missing Convergence Armor ([668be41](https://github.com/Hapfel1/er-save-manager/commit/668be41fcc732f54cc883b9f5e515c560f49366e))


---
## 📦 Release 1.2.2
**Released:** May 19, 2026


### 📦 Dependencies

- General: Bump taiki-e/install-action in the github-actions group ([a5dfbd5](https://github.com/Hapfel1/er-save-manager/commit/a5dfbd58fb066fb6668f2694b8e7bbbc075d5516))


---
## 📦 Release 1.2.1
**Released:** May 14, 2026


### 🔧 Bug Fixes

- General: Inventory update operations and crashing issue ([9faf298](https://github.com/Hapfel1/er-save-manager/commit/9faf298484412d772981df6c0bd24af8974eb808))

- General: Fixed Convergence IDs that collided with base game IDs overwriting base game item names on non convergence saves ([077e6ba](https://github.com/Hapfel1/er-save-manager/commit/077e6baead17ae130760a4c8ec49ad08c88e8ad0))

- General: Fixed icon display issues, updated database ([b2e399a](https://github.com/Hapfel1/er-save-manager/commit/b2e399a4be072e26e1391ca7710b61e991c636e9))

- General: Fix nyasu import to correctly import talisman pouches and memory slots ([864c4a2](https://github.com/Hapfel1/er-save-manager/commit/864c4a22f6180cb321fb4d141397dd49aa867a5b))


### 🎨 User Interface

- General: Added view as icons for all items to make it  more user friendly ([89d17b6](https://github.com/Hapfel1/er-save-manager/commit/89d17b6857f41b4dca17c652314f4fb69f515467))

- General: Added Visual Inventory ([0df8d9b](https://github.com/Hapfel1/er-save-manager/commit/0df8d9b4bdbef98d645640d308f8f7dea39014ff))

- General: Added full visual Item Picker ([3950e72](https://github.com/Hapfel1/er-save-manager/commit/3950e72f6bccf55b57ec334be7518f2ad8339a6e))

- General: Increased Font Size and centered all new popups ([f92ea6b](https://github.com/Hapfel1/er-save-manager/commit/f92ea6b69d882328df02044c8d3e160da4cc0225))


---
## 📦 Release 1.2.0
**Released:** May 12, 2026


### ✨ New Features

- General: Added more modification to existing items in inventory (set affinity, aow, upgrade level) with the correct validation ([159a601](https://github.com/Hapfel1/er-save-manager/commit/159a6018f74989a1a01c4f8dea17a1a0ab2be5bc))


### 🔧 Bug Fixes

- General: Fixed unkown item ids showing up ([6698c2f](https://github.com/Hapfel1/er-save-manager/commit/6698c2f05bc5b244df41f4304c4a3bf5601e8beb))

- General: Fixed Weapon mm level calculation ([4556ba3](https://github.com/Hapfel1/er-save-manager/commit/4556ba3e32a0a82989f9f837ba5b7282d7d19e03))

- General: Correct EF tear false positive and remove unreliable anchor override ([1b7c7e0](https://github.com/Hapfel1/er-save-manager/commit/1b7c7e0d9a592ef511e9e72f24a41cd5c014f38a))

- General: Fix update inventory ops with rebuild to fix crashing issue

Co-authored-by: Copilot <copilot@github.com> ([677bb93](https://github.com/Hapfel1/er-save-manager/commit/677bb930ccca2f75c44c19d8f2874f700dcd82d5))

- General: Improve Item Spawning to avoid crashing/corruption ([debf795](https://github.com/Hapfel1/er-save-manager/commit/debf7959cde268f132e0303178098e1de16a2b94))

- General: Fixed Item Import and slot rebuild to cause more corruption issues ([9ec6054](https://github.com/Hapfel1/er-save-manager/commit/9ec6054a8a73c6a2f82c5e99c246b204e28c2100))

- General: Add maxrepositorynum ([bfed293](https://github.com/Hapfel1/er-save-manager/commit/bfed293b477573096afa0f436f4ca77ca04a6235))


### 🎨 User Interface

- General: Add ItemGib button ([05c9c1f](https://github.com/Hapfel1/er-save-manager/commit/05c9c1f0cc1783d7a871390a5467603c2418919b))


### 📦 Dependencies

- General: Bump taiki-e/install-action in the github-actions group ([8a4c888](https://github.com/Hapfel1/er-save-manager/commit/8a4c888890363c0405b45c90c485251245acc06c))


---
## 📦 Release 1.1.0
**Released:** May 04, 2026


### ✨ New Features

- General: Structured item data with param validation ([28b5b84](https://github.com/Hapfel1/er-save-manager/commit/28b5b84a8faa034d9de3872aba9ad3cd3c9d8d3d))


### 🔧 Bug Fixes

- General: Remove_item was ignoring the delta return value so it did not shift the offsets correctly ([7cccd3d](https://github.com/Hapfel1/er-save-manager/commit/7cccd3d76df24b8a924763ecb1961862dc48db44))

- General: Converted Database files to csv, added more params to validate each spawned item, split up add_item function ([a18ef1f](https://github.com/Hapfel1/er-save-manager/commit/a18ef1f8290461ff896efd620240faf5e60f7cbd))


### 📦 Dependencies

- General: Bump taiki-e/install-action in the github-actions group ([0d73cd8](https://github.com/Hapfel1/er-save-manager/commit/0d73cd8d90d4ed2eb8d708c374549d284afc2c06))


---
## 📦 Release 1.0.0
**Released:** May 03, 2026


### ✨ New Features

- General: Added Item Spawning ([2bf7b41](https://github.com/Hapfel1/er-save-manager/commit/2bf7b4165f56a02c55d73f398515a2ab87d6f3db))

- General: Added Equipment Editing ([c6aef6e](https://github.com/Hapfel1/er-save-manager/commit/c6aef6e27113ca6ee01332580ae059fa0db410c9))

- General: Added Item Spawning ([3569e06](https://github.com/Hapfel1/er-save-manager/commit/3569e067163db9287daad2740381cbf9b9379f00))

- General: Release v1.0.0 ([d54a0de](https://github.com/Hapfel1/er-save-manager/commit/d54a0de00aefca7388629e4877c8db655d1b37b6)) ⚠️ **BREAKING CHANGE**


### 🔧 Bug Fixes

- General: Fixed equipment editor not creating backups ([67abf43](https://github.com/Hapfel1/er-save-manager/commit/67abf43839062a0e6f56f8e67a549d4c787dd847))

- General: Fixed deep scan issues ([678a99a](https://github.com/Hapfel1/er-save-manager/commit/678a99ad33664e6f2246173cbe9c7936b9c2f803))


### 🎨 User Interface

- General: Rework vanilla save warning ([c73b2ca](https://github.com/Hapfel1/er-save-manager/commit/c73b2ca8776b604e66b9151b9235b773b38e6642))

- General: Remade Inventory Editor UI and added Affinities ([777eb0d](https://github.com/Hapfel1/er-save-manager/commit/777eb0d4a666a5fb8c8209f903f50f1a5ac4a89e))


### 📦 Dependencies

- General: Bump taiki-e/install-action in the github-actions group ([288d056](https://github.com/Hapfel1/er-save-manager/commit/288d056ec55d43455a8364f9d66da5bcfb75fbc8))


---
## 📦 Release 0.14.1
**Released:** April 22, 2026


### 🔧 Bug Fixes

- General: Add replacenetman option and button for trashed csnetmans without visible write torns ([23ff547](https://github.com/Hapfel1/er-save-manager/commit/23ff5474f5db3fab3133dcde17af8e862b8dbd3e))

- General: Fixed steamid not being synced correctly when importing from a .erc file ([4d3c9d9](https://github.com/Hapfel1/er-save-manager/commit/4d3c9d91bb0ab9f2dae405e6f0fa49ecbcd85ff2))


### 🎨 User Interface

- General: Add import flags button and add "All" selection for event flag categories with subcategories ([9c87496](https://github.com/Hapfel1/er-save-manager/commit/9c874962f3f64c05f831de3dfd2b337911a9372b))

- General: Added Playtime Editor ([555ed85](https://github.com/Hapfel1/er-save-manager/commit/555ed85fca02ea6924baa1be42fdb0173214cc8b))


### 📦 Dependencies

- General: Bump the github-actions group with 2 updates ([173e6f1](https://github.com/Hapfel1/er-save-manager/commit/173e6f1287b3165f094ac2eccfbe7874c316e42b))

- General: Bump the github-actions group with 2 updates ([1f9f899](https://github.com/Hapfel1/er-save-manager/commit/1f9f8998cc0b27a6bad36babf840c61294387517))


---
## 📦 Release 0.14.0
**Released:** April 10, 2026


### ✨ New Features

- General: Add weapon_matchmaking_level and a check for every weapon upgrade level to combat any tries to abuse modifying it ([e715c02](https://github.com/Hapfel1/er-save-manager/commit/e715c02793ab2d6757911f0510977eeff2563248))


### 🔧 Bug Fixes

- General: Fixed SteamID auto-detection on Linux ([debc036](https://github.com/Hapfel1/er-save-manager/commit/debc036c555521cf1f1116ce10187b8922ef8d23))

- General: Fixed Steam vanity link parsing ([150ed43](https://github.com/Hapfel1/er-save-manager/commit/150ed43545e3b570a17b588e95b5b46cb57f5f63))

- General: Fix Open folder button on certain Linux distros not working ([ca4edd0](https://github.com/Hapfel1/er-save-manager/commit/ca4edd01297a5e80d4b438740fd2f7ad83794529))

- General: Fixed the upgrade level detection ([33c9f5d](https://github.com/Hapfel1/er-save-manager/commit/33c9f5dfb55d49c0e2b7c0913a2e24d01a8c1c8f))

- General: Fixed process monitoring ([f9dfad4](https://github.com/Hapfel1/er-save-manager/commit/f9dfad4e5d7fd6130918170791b655ac53e31db9))

- General: Fixed process detection for is_game_running ([31eb4e9](https://github.com/Hapfel1/er-save-manager/commit/31eb4e9bb6c66936e0f38c624fb3312f0bdb9589))

- General: Fixed character name not being read correctly because of garbage data ([a5b40e1](https://github.com/Hapfel1/er-save-manager/commit/a5b40e15842515c940cf4023a838c0f1dfc52a96))

- General: Format and lint ([d4c374c](https://github.com/Hapfel1/er-save-manager/commit/d4c374c56ea08d1a1832cecf50f889fd5d392d9e))

- General: Fixed png issue with character browser and impoved loading in the browser ([3e74123](https://github.com/Hapfel1/er-save-manager/commit/3e741233895a947f15544551468d535a4cdedb37))

- General: Fixed cpu0 feature not applying correctly ([b6ad4a7](https://github.com/Hapfel1/er-save-manager/commit/b6ad4a7beac5779882b406f9430363c3daec5872))

- General: Lint ([62fab68](https://github.com/Hapfel1/er-save-manager/commit/62fab6810fb5c1bee51d972c7b438e42ad48fbb7))


### 🎨 User Interface

- General: Add "Apply CPU 0 fix on game launch" setting for ER, NR and DS3 ([158aedd](https://github.com/Hapfel1/er-save-manager/commit/158aedd53eec8f9d174e95f0387cde299d1a05eb))

- General: Fix performance issues ([04c441f](https://github.com/Hapfel1/er-save-manager/commit/04c441f8ad1e9b4be05521c15e2a9541306e9673))


### 📦 Dependencies

- General: Bump taiki-e/install-action in the github-actions group ([4f2a231](https://github.com/Hapfel1/er-save-manager/commit/4f2a231eeaf42e49b140a7ab47d158ddd6dbcbd7))


### Buld

- General: Lint ([181f197](https://github.com/Hapfel1/er-save-manager/commit/181f19778770e89527be95b464d155715fe0095d))


---
## 📦 Release 0.13.0
**Released:** April 02, 2026


### ✨ New Features

- General: Added Invasion Regions and ingame settings ([e674007](https://github.com/Hapfel1/er-save-manager/commit/e67400780232383d721e675b0085280d1af41bb5))

- General: Add other Fromsoft Games for SteamID Patching and Backup Manager ([b1d6e4b](https://github.com/Hapfel1/er-save-manager/commit/b1d6e4b5325172193f4c6fd4ad9b5f4bbbe5c527))

- General: Added "Move Bloodstain to player" button in the world state tab ([fed05c7](https://github.com/Hapfel1/er-save-manager/commit/fed05c7c55d8a8a4e06a6b2646c9b70b3ee56793))


### 🔧 Bug Fixes

- General: Fix event flag custom id toggle not creating backups ([7eae089](https://github.com/Hapfel1/er-save-manager/commit/7eae0894387cbef99f36912529d4a041e2e82a39))

- General: Fixed rendering issue in Appearance Tab popup window ([f8fc349](https://github.com/Hapfel1/er-save-manager/commit/f8fc3496e5b00fb547d3d1aae121b3c65ade97c0))

- General: Added change files ([b502a78](https://github.com/Hapfel1/er-save-manager/commit/b502a786ce1d3ff184d92b2c63ad7f3eca60f6bb))

- General: Lint ([2c6d07c](https://github.com/Hapfel1/er-save-manager/commit/2c6d07c608709e935df37d29949d1ea0a18ed4c9))

- General: Added correct functionality for steamid patching for each game ([6210337](https://github.com/Hapfel1/er-save-manager/commit/6210337fa7c9b01612eecb71baecec338d5d4bb5))

- General: Fixed Save Loading and Process detection for Non-ER games ([31c48d9](https://github.com/Hapfel1/er-save-manager/commit/31c48d90f717d909d7a38bb967a9c6b855d3d411))


### 🎨 User Interface

- General: Add Event Flag Export ([9378421](https://github.com/Hapfel1/er-save-manager/commit/9378421cd6452a11828594a33da56052ef5a4415))

- General: Added Great Rune and Rune Arc display ([61ac096](https://github.com/Hapfel1/er-save-manager/commit/61ac0962801aa6da40795486990666ad08634717))

- General: Fixed popup centering ([1ceb5dc](https://github.com/Hapfel1/er-save-manager/commit/1ceb5dcd25c62eff97eec2f2c767e93cb1c4aeac))

- General: Added warning when no apperance presets are saved to first save one in game ([580b149](https://github.com/Hapfel1/er-save-manager/commit/580b1490692dedbc6ca4d5c65e5f37449fb582be))

- General: Add MapID map for the known locations teleport feature ([ef62ebc](https://github.com/Hapfel1/er-save-manager/commit/ef62ebc55a6f29aa4e813b2a38a65ce9f5d43d64))


### 📦 Dependencies

- General: Bump the github-actions group with 3 updates ([61ca83d](https://github.com/Hapfel1/er-save-manager/commit/61ca83d842fe5ed53ed9920818b0b8bf41215ebc))


---
## 📦 Release 0.12.1
**Released:** March 23, 2026


### ✨ New Features

- General: Added Event Flag Torn Detection and Fix ([baa2948](https://github.com/Hapfel1/er-save-manager/commit/baa2948623073ab6b7fdb73bc3f7134361c087ab))


### 🔧 Bug Fixes

- General: Fixed last opened save location not working on Linux ([a6edd49](https://github.com/Hapfel1/er-save-manager/commit/a6edd4938e37a98267ba67a1a4e1f6eb9a2362b6))

- General: Add netman validation and corruption fixing after byteshift ([107a868](https://github.com/Hapfel1/er-save-manager/commit/107a86860244e634a16e79d1f46c05dcc83cdf9f))

- General: Fixed dlc flag detection + added apply button when only checking that checkbox ([ee22bd6](https://github.com/Hapfel1/er-save-manager/commit/ee22bd6101fc0e9d4db8dfd68586eb6d49a12dc2))

- General: Added Checksum validation for slots ([9928ad6](https://github.com/Hapfel1/er-save-manager/commit/9928ad6da245b0e08546b5ca4f9156cb24725c0a))

- General: Added event flags for npc quests and a tab for checking progress ([e9a17b8](https://github.com/Hapfel1/er-save-manager/commit/e9a17b8aa38ff9e448a4350179075fffae36b8d4))


### 🎨 User Interface

- General: Add button that links to discord server ([b3f8d8a](https://github.com/Hapfel1/er-save-manager/commit/b3f8d8a5c7b5e18f066d291c4fdaedbdbc902b05))

- General: Made popups from character_details appear centered over its parent ([8e1197f](https://github.com/Hapfel1/er-save-manager/commit/8e1197f4337875b70e785ea3710cca72f6b43794))


### 📦 Dependencies

- General: Bump the github-actions group with 2 updates ([4af85db](https://github.com/Hapfel1/er-save-manager/commit/4af85db09392fb47652ba599876aa7ee9dfd77c6))

- General: Bump taiki-e/install-action in the github-actions group ([b11b53d](https://github.com/Hapfel1/er-save-manager/commit/b11b53dc0dc879e61d19d7ca89d05115273a3487))


---
## 📦 Release 0.11.1
**Released:** March 14, 2026


### 🔧 Bug Fixes

- General: Fix: use data_start consistently
864a98e converted the offsets from slot-relative to absolute, but only
in the slot itself - all of the other scripts still expected it to have
been removed and would re-add the slot data offset back in, corrupting
the pointer and trashing the save slot. This removes the slot offset
addition from all of the places where the slot data offset is already
present in the slot object itself, preventing corruption ([93246a2](https://github.com/Hapfel1/er-save-manager/commit/93246a28010be7adfbfb560a4fd16da2699c703c))

- General: Fixed offsets being applied twice ([dc6a7da](https://github.com/Hapfel1/er-save-manager/commit/dc6a7da855b98758aa8a96a1585fb96363207037))


---
## 📦 Release 0.11.0
**Released:** March 13, 2026


### ✨ New Features

- General: Add NPC respawner ([270e0de](https://github.com/Hapfel1/er-save-manager/commit/270e0de67c14b9af76d6d75faa63ac0d076da558))

- General: Added known locations to the World State Tab for teleporting ([50ba6d7](https://github.com/Hapfel1/er-save-manager/commit/50ba6d73e99887c5b7a881e9c949784c61d9524a))

- General: Added more save file corruption detection and Fixes ([864a98e](https://github.com/Hapfel1/er-save-manager/commit/864a98ebf4d560131487b0d417c3518f69b6a258))


### 🔧 Bug Fixes

- General: Fixed window popup render issue on linux ([375375a](https://github.com/Hapfel1/er-save-manager/commit/375375a1f5beb9c5e2475aa892c3d34b5a0b7baa))

- General: Fixed SteamID Patcher AutoDetection ([cbdd7d4](https://github.com/Hapfel1/er-save-manager/commit/cbdd7d455bc2f352f829bc55e355741470da95b3))

- General: Fixed scrolling on Linux ([8fa53d5](https://github.com/Hapfel1/er-save-manager/commit/8fa53d5f6488bde378e4039fdd84f459c7cd8b89))

- General: Fixed Character Operations also copying ProfileSummary so that the character gets shown correctly instantly ([50c90c5](https://github.com/Hapfel1/er-save-manager/commit/50c90c5031bf2279b4c31261a181c96d40ec3d4e))


### 🎨 User Interface

- General: Made game running detection more clear and added a button to force quit the game ([9d7afcf](https://github.com/Hapfel1/er-save-manager/commit/9d7afcfa7639946b1b572b138e412c9d6c1d7131))

- General: Added new Toast info boxes to remove popup spam ([fe91822](https://github.com/Hapfel1/er-save-manager/commit/fe9182218e56ff7b1880403f1ee80abe60268f29))

- General: Remade Troubleshooting button to offer an Addon install for the standalone troubleshooter ([298e1a6](https://github.com/Hapfel1/er-save-manager/commit/298e1a6a20ec5433e46581ce80730ee3aa3dcf6a))

- General: Changed some info popups to be Toast notifications instead for a better UX ([27ee698](https://github.com/Hapfel1/er-save-manager/commit/27ee698a1555267f889cc337d3bb2d807bd367d7))

- General: Added character names next to the slot selections everywhere ([85be34e](https://github.com/Hapfel1/er-save-manager/commit/85be34ecacbf1c56e171263e159a4009c6bb279e))


---
## 📦 Release 0.10.1
**Released:** February 11, 2026


### 🔧 Bug Fixes

- General: Fix : fix character ops error ([9c60a4c](https://github.com/Hapfel1/er-save-manager/commit/9c60a4c5633608ada3b03a5f6666df2725f720b5))


---
## 📦 Release 0.10.0
**Released:** February 10, 2026


### ✨ New Features

- General: Added Auto-Backup Feature when booting up the game, changed backups to be zipped by default. ([12c562c](https://github.com/Hapfel1/er-save-manager/commit/12c562cb0fa3eb0258ac8943bc08cbafeb64a423))

- General: Added Character Browser ([c4199f7](https://github.com/Hapfel1/er-save-manager/commit/c4199f77a20d57d7a15545531e7e9b8f6c74913e))

- General: Add Convergence Support for the Character Browser ([b31d77f](https://github.com/Hapfel1/er-save-manager/commit/b31d77f0b258208d7edf229a2f268608a3a0581e))


### 🔧 Bug Fixes

- General: Fixed appimage build to include the custom lavender theme correctly ([69b044c](https://github.com/Hapfel1/er-save-manager/commit/69b044ceb1436dcf3c82b066c6f085919d82d61c))

- General: Added vpn checker in troubleshooting tab ([d81e4e9](https://github.com/Hapfel1/er-save-manager/commit/d81e4e9ef5f94f51a283ee8c651fbc7e00f83853))

- General: Added error for if the program is being run while zipped ([e6f5508](https://github.com/Hapfel1/er-save-manager/commit/e6f5508a370671feba144cd5e3e4c9876461360a))

- General: Fix steamdeck resolution issue ([40188fa](https://github.com/Hapfel1/er-save-manager/commit/40188fa015e5ac607b9b6ed31f95abd729090715))

- General: Fixed wrong cnv save detection ([ebaecf7](https://github.com/Hapfel1/er-save-manager/commit/ebaecf790dc366bdd81f97b8285ef359d4d19255))

- General: Fixed error when copying characters because of invalid filename characters, added sanitization ([efa87ad](https://github.com/Hapfel1/er-save-manager/commit/efa87ad8fecca4b0a2214add81760e3bf5febf2a))

- General: Made opening links work on Linux ([3d33715](https://github.com/Hapfel1/er-save-manager/commit/3d337153c245ed5576aa8136d7fc59b70b1af1ea))

- General: Fixed transferring characters between Save Files to correctly update Profile Summary and fixed an offset tracking error ([e4de080](https://github.com/Hapfel1/er-save-manager/commit/e4de08040c2abe1ff0abcec356133a79bd6bc31b))


### 🎨 User Interface

- General: Made autobackup more clear and easier to use ([f11c910](https://github.com/Hapfel1/er-save-manager/commit/f11c910fd91849483694d1f1fe334fce4dab6aac))

- General: Revamped UI to work better for small resolution displays ([9f13ef9](https://github.com/Hapfel1/er-save-manager/commit/9f13ef99178c8bc900bc0cdbb4c2ef4f2337e39d))


### 📖 Documentation

- General: Updated TODO ([8c165dd](https://github.com/Hapfel1/er-save-manager/commit/8c165dd5b27212585c76555603ef425ae83eef68))


### Buld

- General: Edit todo ([e14dd3e](https://github.com/Hapfel1/er-save-manager/commit/e14dd3ee7d0181deb1f85170307865e5dfbdfa9e))


---
## 📦 Release 0.9.0
**Released:** February 03, 2026


### ✨ New Features

- General: Added export to JSON preset selection ([a72d783](https://github.com/Hapfel1/er-save-manager/commit/a72d783b724798d24d30fd786a282f675c16abba))


### 🔧 Bug Fixes

- General: Correct case sensitivity for theme path on Linux ([7c2a48a](https://github.com/Hapfel1/er-save-manager/commit/7c2a48a698216e4dcfcdd7692078dba127d65626))

- General: Fixed event flags being written incorrectly ([cc49186](https://github.com/Hapfel1/er-save-manager/commit/cc491863ecdb44fbb60599d33b21d7115b8913c3))

- General: Fixed save file backup functionality ([f44c7e6](https://github.com/Hapfel1/er-save-manager/commit/f44c7e65d44fd8688068631fdcf9f7fde79921b1))

- General: Fixed Character operation issues ([70080fb](https://github.com/Hapfel1/er-save-manager/commit/70080fbaba8c68246ad5e796f3a6698b9969cfdb))

- General: Fixed info message popups appearing behind main window ([69162ad](https://github.com/Hapfel1/er-save-manager/commit/69162ad08cb60707c0f982b923e8852ce1c1cc56))


---
## 📦 Release 0.8.0
**Released:** February 02, 2026


### ✨ New Features

- General: Added version checker to notify users of new update ([9d49382](https://github.com/Hapfel1/er-save-manager/commit/9d49382af93792e0762eb4572c94c02ecf41ea17))

- General: Add Troubleshooter for checking game und save file related issues ([4eb53b7](https://github.com/Hapfel1/er-save-manager/commit/4eb53b7c073e6d412fb5bcd48314f69b124829bf))


### 🔧 Bug Fixes

- General: Fixed SteamDeck not showing Preset Browser correctly bc of SSL errors ([c6496ce](https://github.com/Hapfel1/er-save-manager/commit/c6496ce5fd604f41e2425caf74d23e23c7826ce3))


---
## 📦 Release 0.7.4
**Released:** January 31, 2026


### 🔧 Bug Fixes

- General: Fixed JSON import error msg ([aa67a3b](https://github.com/Hapfel1/er-save-manager/commit/aa67a3b5617b5cfe063668b774227a7dad34795c))


### 🎨 User Interface

- General: Change default theme to dark ([25a2a64](https://github.com/Hapfel1/er-save-manager/commit/25a2a64c291844c67648573972d953f3ea942c26))


---
## 📦 Release 0.7.3
**Released:** January 30, 2026


### ✨ New Features

- General: Add ng+ editor in character info tab ([b79a135](https://github.com/Hapfel1/er-save-manager/commit/b79a1358710cd42716ffcdcb5b666e7c1dc88221))


### 🔧 Bug Fixes

- General: Changed image display in the preset browser to always display the original image's resolution ([5f5d609](https://github.com/Hapfel1/er-save-manager/commit/5f5d609bc72574fde4ad38ddc46a7cc2f40485bd))


### 🎨 User Interface

- General: Make save fixer description more clear and add auto loading upon selecting a save file ([3df841b](https://github.com/Hapfel1/er-save-manager/commit/3df841b162422759694165893adb71c99dc9885b))

- General: Made all message boxes custom and improved the messagebox module ([8db333e](https://github.com/Hapfel1/er-save-manager/commit/8db333e84a379c42fb7f3be1107643456a20c015))

- General: Centered all popups to be in the middle of the parent's window ([e04cc7d](https://github.com/Hapfel1/er-save-manager/commit/e04cc7d3d820dad961f0875ea938eac28bc516c7))


### 📖 Documentation

- General: Update TODO ([6f0fd88](https://github.com/Hapfel1/er-save-manager/commit/6f0fd88b372f6c650d6a8c9064822c3027c009ac))


---
## 📦 Release 0.7.2
**Released:** January 30, 2026


---
## 📦 Release 0.7.1
**Released:** January 28, 2026


### 🔧 Bug Fixes

- General: Fixed error message pop-up when no actual error happened ([0ce4231](https://github.com/Hapfel1/er-save-manager/commit/0ce42314ce6e2e6cda7ff7dd2fd57ce0fa503d23))


---
## 📦 Release 0.7.0
**Released:** January 28, 2026


### ✨ New Features

- General: Add DLC flag clearing with conditional UI and teleport integration ([9b2c7b9](https://github.com/Hapfel1/er-save-manager/commit/9b2c7b94ff311220969a3a49a437e297222867aa))


### 🔧 Bug Fixes

- General: Made all tabs scrollable, fixed typo ([320f047](https://github.com/Hapfel1/er-save-manager/commit/320f0474fc2590e0cf6b6dd22ea69bd4e8c99c43))

- General: Format & lint ([155c326](https://github.com/Hapfel1/er-save-manager/commit/155c3262a01242143a48e6a294af7d7e6ccd9f66))


### 🎨 User Interface

- General: Fixed color issue in bright mode with character editor tab ([448b08d](https://github.com/Hapfel1/er-save-manager/commit/448b08d70e5a56a4336f9b8829453ddace07c78b))


---
## 📦 Release 0.6.2
**Released:** January 27, 2026


### 🔧 Bug Fixes

- General: Fixed workflow version numbering ([201ec8d](https://github.com/Hapfel1/er-save-manager/commit/201ec8da2587bf7d9a93a7983ef155355a39319d))


---
## 📦 Release 0.6.1
**Released:** January 27, 2026


### 🔧 Bug Fixes

- General: Fixed version  bumping to include manifest and version info file ([1af05de](https://github.com/Hapfel1/er-save-manager/commit/1af05de2a757b62618836b5f767e4c97b8c309e9))


---
## 📦 Release 0.6.0
**Released:** January 27, 2026


### ✨ New Features

- General: Apply dark theme to character editor and fix CTkMessageBox calls ([15cfbb4](https://github.com/Hapfel1/er-save-manager/commit/15cfbb47c894e3174b73be6ddb1736e427911a3a))

- General: Community preset system with metrics, voting, and reporting ([d2f5a0a](https://github.com/Hapfel1/er-save-manager/commit/d2f5a0ab028f653d3dba11edddee957ed120049f))

- General: Cross-platform save file detection and Linux steam path improvements ([f4954a2](https://github.com/Hapfel1/er-save-manager/commit/f4954a247f6d466f2205968e34b3130ece91ffe3))


### 🔧 Bug Fixes

- General: Improve save file loading and compatdata warnings ([2d3332c](https://github.com/Hapfel1/er-save-manager/commit/2d3332c28396d52845be06e66db294817b4d2db3))

- General: Format & lint ([6112d26](https://github.com/Hapfel1/er-save-manager/commit/6112d26d79c5c267e2b689bc6e25b82cdacbe8db))

- General: Fixed issues when running the appimage on linux ([427011a](https://github.com/Hapfel1/er-save-manager/commit/427011a39eb16c964eb3feaa1a56868a102f28c7))

- General: Fix: linux tab rendering fixes
build: added logging to find out issue with appearance browser ([7737830](https://github.com/Hapfel1/er-save-manager/commit/77378301ae20f22c277887f9035c04e81f3d4e6c))

- General: Format & lint ([6281eb0](https://github.com/Hapfel1/er-save-manager/commit/6281eb028873de252bb8665eb954da589d2343ba))

- General: Fix: Fixed PIL/Tkinter ingegration for Linux
Fixed Resource loading
Fixed "grab failed" issues ([f9cf8a3](https://github.com/Hapfel1/er-save-manager/commit/f9cf8a318f90d1121c84881337314e19b1859cc8))

- General: Fixed eventflag binary search tree text file loading on linux ([e58634c](https://github.com/Hapfel1/er-save-manager/commit/e58634c1193b9e335000169876e7e23fc36baa89))

- General: Fixed correct resources import ([6b58161](https://github.com/Hapfel1/er-save-manager/commit/6b581618baba8c33c160c332d032b409942d0728))


### 🎨 User Interface

- General: Enhance preset browser and application UI ([2a4bfaa](https://github.com/Hapfel1/er-save-manager/commit/2a4bfaa9b1588344fb956bf69d2c05142185a785))


### 📖 Documentation

- General: Complete documentation rewrite with feature status and architecture ([25a377a](https://github.com/Hapfel1/er-save-manager/commit/25a377a4bf8fdd4d19917e256a8df6880e5400eb))

- General: Fixed documentation ([0936903](https://github.com/Hapfel1/er-save-manager/commit/09369034d090ad99e97170d343d187d83e76ad6e))


### ⚡ Performance Improvements

- General: Optimize preset browser loading and caching ([7bfe8b6](https://github.com/Hapfel1/er-save-manager/commit/7bfe8b6e09592ad2a27ecfe3c150c5a85d33fe1d))


### 🧹 Maintenance

- General: Fix gitignore to track source data and fix region_ids_map ([f3f10a0](https://github.com/Hapfel1/er-save-manager/commit/f3f10a0d2148277bba22faeaf003a86c738f1c39))


---
## 📦 Release 0.5.1
**Released:** January 24, 2026


### 🔧 Bug Fixes

- General: Fixed import/export ([5b43c5f](https://github.com/Hapfel1/er-save-manager/commit/5b43c5f6b69850fdd39bc0398607810d5b3eaef0))

- General: Format & lint ([62f285f](https://github.com/Hapfel1/er-save-manager/commit/62f285f9fb5ccc7bd592cab9c46b205cc7de1208))


---
## 📦 Release 0.5.0
**Released:** January 24, 2026


### ✨ New Features

- General: Major UI improvements and bug fixes ([ff797d2](https://github.com/Hapfel1/er-save-manager/commit/ff797d2a5136d72f5388c41cf2ee4555a07b5a22))

- General: Complete SteamID patcher with custom URL resolution ([5693746](https://github.com/Hapfel1/er-save-manager/commit/56937465fda1f2f53b6bb1831a1ee4c2e7ef8dd4))

- General: Implement comprehensive event flags and gestures systems ([2cfa82d](https://github.com/Hapfel1/er-save-manager/commit/2cfa82df244a41df1cacbba657d34d021eeb54f3))

- General: Implement boss respawn function (not finished) ([31f0af3](https://github.com/Hapfel1/er-save-manager/commit/31f0af34b8c95bf8f8b6966b6ea531800868ce10))

- General: Implement complete community character preset browser system ([0473d4d](https://github.com/Hapfel1/er-save-manager/commit/0473d4d51589a3c241f8e3da5a004ae110d729a2))


### 🔧 Bug Fixes

- General: Small removal ([22ad8e0](https://github.com/Hapfel1/er-save-manager/commit/22ad8e089e83a784ce80410020d15cbc053e9770))

- General: Fix: removed temporary testing buttons
docs: updated tooltips for boss respawner ([4e1610c](https://github.com/Hapfel1/er-save-manager/commit/4e1610c7111bbb4ce8fa217da0d9fe66a6b77ca1))

- General: Lint % format ([2e4ca4c](https://github.com/Hapfel1/er-save-manager/commit/2e4ca4cbfc45afff3fcb8b04a76f2c016a76e29b))

- General: Fix: small fixes for UI
fix: fix appearance browser + add workflow for submission ([f10476e](https://github.com/Hapfel1/er-save-manager/commit/f10476efd0983468b788ab01a65e5f28e23dbe55))


### 📖 Documentation

- General: Updated TODO.md ([9673787](https://github.com/Hapfel1/er-save-manager/commit/96737878702ced21cda66e8a4da753b759f47e9f))

- General: Updated TODO ([34cd7d2](https://github.com/Hapfel1/er-save-manager/commit/34cd7d2110a8a62b4cc5c6745d43f41368491a3d))


---
## 📦 Release 0.4.1
**Released:** January 23, 2026


### 🔧 Bug Fixes

- General: License format in pyproject.toml to combat deprecation warning ([00c9eed](https://github.com/Hapfel1/er-save-manager/commit/00c9eed93219f627ddb843aaac646e40ea919c6b))

- General: Fix deprecation issue with license ([c4834ef](https://github.com/Hapfel1/er-save-manager/commit/c4834ef1f9de5aa93276a7e442312be44f1f5d02))


---
## 📦 Release 0.4.0
**Released:** January 18, 2026


### ✨ New Features

- General: Add modular UI components ([c2f1997](https://github.com/Hapfel1/er-save-manager/commit/c2f1997664666a612bf72b0f48a8401b14a97cf8))

- General: Add modular GUI coordinator ([3c91776](https://github.com/Hapfel1/er-save-manager/commit/3c91776ffbac9357366b16a0b1504866ed3bf9c7))

- General: Add item database for user-friendly names ([b78fc48](https://github.com/Hapfel1/er-save-manager/commit/b78fc48571ad18cb7edc44da4afa0e06ac7db0f5))


### 🔧 Bug Fixes

- General: Fixed cli to integrate new ui modules ([61a8b6d](https://github.com/Hapfel1/er-save-manager/commit/61a8b6dd03c161e98ed0229dffc28f6985467083))

- General: Update parser for GUI compatibility ([67d2019](https://github.com/Hapfel1/er-save-manager/commit/67d2019358077caa02e09d220c2f1feda30adf66))

- General: Format and lint ([37de52f](https://github.com/Hapfel1/er-save-manager/commit/37de52fcb3384ab3c8cd817c96221e67c948b6db))


### 🧹 Maintenance

- General: Update TODO and backup original GUI ([bc3bc46](https://github.com/Hapfel1/er-save-manager/commit/bc3bc463fb8e1e3746ddadc7aeec0aad8a1cf64b))


---
## 📦 Release 0.3.0
**Released:** January 17, 2026


### ✨ New Features

- General: Add character operations module with dynamic offset tracking ([d8d58f8](https://github.com/Hapfel1/er-save-manager/commit/d8d58f8f241bde751c67f886d985cdf0876b63c8))

- General: Implement dynamic offset tracking in save parser ([d77305e](https://github.com/Hapfel1/er-save-manager/commit/d77305ee0952193ad36ec053a9c35838e3f732aa))


### 🎨 User Interface

- General: Redesign character management with operation dropdown ([609a478](https://github.com/Hapfel1/er-save-manager/commit/609a478c3ab395292940de0c9bccaa2b499ccf0f))


### 📖 Documentation

- General: Updated TODO.md ([2115d99](https://github.com/Hapfel1/er-save-manager/commit/2115d99d5f78fc9208f7648c49990bd1708ba443))


---
## 📦 Release 0.2.1
**Released:** January 17, 2026


### 🔧 Bug Fixes

- General: Convert all relative imports to absolute ([5ea6078](https://github.com/Hapfel1/er-save-manager/commit/5ea607892896cabe1e5ac3b37d784dc891c1669d))


### 📖 Documentation

- General: Add TODO file with feature implementation roadmap ([e28e577](https://github.com/Hapfel1/er-save-manager/commit/e28e57723929dfde22919d109195c85374e0eaf9))


---
## 📦 Release 0.2.0
**Released:** January 17, 2026


### ✨ New Features

- General: Add GUI launcher and fix Windows executable ([12f4911](https://github.com/Hapfel1/er-save-manager/commit/12f4911bd141bb660d13bd276d0d5aa8288259d4))


### 🔧 Bug Fixes

- General: Use absolute import for cx_Freeze compatibility ([ecabaf3](https://github.com/Hapfel1/er-save-manager/commit/ecabaf3834da0cccdec487aae9c2d52e69a1a55b))

- General: Convert all relative imports to absolute for cx_Freeze compatibility ([cf39803](https://github.com/Hapfel1/er-save-manager/commit/cf3980334b81b4cfdbb82efee0b115da3762b2c4))

- General: Test auto release trigger ([15f80bc](https://github.com/Hapfel1/er-save-manager/commit/15f80bcbb76495b7db7907b0ed96e55d4b550785))

- General: Release workflow safety check and changelog extraction ([2998705](https://github.com/Hapfel1/er-save-manager/commit/299870540cf9b922bd07cf8a80073d0407d8f564))

- General: Correct PR URL in cliff.toml template ([e4b2d56](https://github.com/Hapfel1/er-save-manager/commit/e4b2d564e1d73cd6dbd338f7f98abbb1cbb18283))


### 🧹 Maintenance

- General: Re-trigger release for 0.1.1 ([765b99d](https://github.com/Hapfel1/er-save-manager/commit/765b99d65c89c5cb5851025640ea7ec86616d1c3))

- General: Update repo URLs to upstream (Hapfel1) ([4402930](https://github.com/Hapfel1/er-save-manager/commit/4402930cf948f4b64a2adbe28fd8c7a113d4c69f))


---
## 📦 Release 0.1.0
**Released:** January 17, 2026


### ✨ New Features

- General: Added release workflow ([1020635](https://github.com/Hapfel1/er-save-manager/commit/1020635c64bc24f759f08f96898aad32f645a44b))

- General: Added gui, implemented functions partially ([252b1a7](https://github.com/Hapfel1/er-save-manager/commit/252b1a7f15b8dc9ed082625f408870f05c7399ef))

- General: Feat: add new gui features (templates for further
implementation) ([19bee2c](https://github.com/Hapfel1/er-save-manager/commit/19bee2ccc54139c84a885afd66f9ff4be65cfc57))

- General: Add automatic release workflow and build scripts ([a3fade6](https://github.com/Hapfel1/er-save-manager/commit/a3fade69b5c24e72567552adfadf474dd57f9480))


### 🔧 Bug Fixes

- General: Edited readme correctly ([08d07c8](https://github.com/Hapfel1/er-save-manager/commit/08d07c8e6e59cae477ffd25d1bbb93287148a154))

- General: README ([68f2635](https://github.com/Hapfel1/er-save-manager/commit/68f263548542be47e011932fe7070e6cc8a9d74f))

- General: Lint and format ([156bdc6](https://github.com/Hapfel1/er-save-manager/commit/156bdc62093d20b8ca476366286b5e28562e035a))

- General: Fix import ([856ca9c](https://github.com/Hapfel1/er-save-manager/commit/856ca9c31fb8168775fbe3739ac7b57702448c2d))

- General: Set executable permissions for shell scripts ([ef832ac](https://github.com/Hapfel1/er-save-manager/commit/ef832ac9777de8880a3191c223a285aad32778eb))

- General: Fix ci.yml ([9b1d27a](https://github.com/Hapfel1/er-save-manager/commit/9b1d27ab844f746377362b23354ee1da1bfee629))


### 🧹 Maintenance

- General: Repo URLs in cliff.toml for upstream ([e889185](https://github.com/Hapfel1/er-save-manager/commit/e889185aa27086d6a4de2d1a25528b3a5d5ee890))


---
[2.0.2]: https://github.com/Hapfel1/er-save-manager/compare/v2.0.1..v2.0.2
[2.0.1]: https://github.com/Hapfel1/er-save-manager/compare/v2.0.0..v2.0.1
[2.0.0]: https://github.com/Hapfel1/er-save-manager/compare/v1.12.2..v2.0.0
[1.12.2]: https://github.com/Hapfel1/er-save-manager/compare/v1.12.1..v1.12.2
[1.12.1]: https://github.com/Hapfel1/er-save-manager/compare/v1.12.0..v1.12.1
[1.12.0]: https://github.com/Hapfel1/er-save-manager/compare/v1.11.0..v1.12.0
[1.11.0]: https://github.com/Hapfel1/er-save-manager/compare/v1.10.3..v1.11.0
[1.10.3]: https://github.com/Hapfel1/er-save-manager/compare/v1.10.2..v1.10.3
[1.10.2]: https://github.com/Hapfel1/er-save-manager/compare/v1.10.1..v1.10.2
[1.10.1]: https://github.com/Hapfel1/er-save-manager/compare/v1.10.0..v1.10.1
[1.10.0]: https://github.com/Hapfel1/er-save-manager/compare/v1.9.1..v1.10.0
[1.9.1]: https://github.com/Hapfel1/er-save-manager/compare/v1.9.0..v1.9.1
[1.9.0]: https://github.com/Hapfel1/er-save-manager/compare/v1.8.0..v1.9.0
[1.8.0]: https://github.com/Hapfel1/er-save-manager/compare/v1.7.1..v1.8.0
[1.7.1]: https://github.com/Hapfel1/er-save-manager/compare/v1.7.0..v1.7.1
[1.7.0]: https://github.com/Hapfel1/er-save-manager/compare/v1.6.2..v1.7.0
[1.6.2]: https://github.com/Hapfel1/er-save-manager/compare/v1.6.1..v1.6.2
[1.6.1]: https://github.com/Hapfel1/er-save-manager/compare/v1.6.0..v1.6.1
[1.6.0]: https://github.com/Hapfel1/er-save-manager/compare/v1.5.2..v1.6.0
[1.5.2]: https://github.com/Hapfel1/er-save-manager/compare/v1.5.1..v1.5.2
[1.5.1]: https://github.com/Hapfel1/er-save-manager/compare/v1.5.0..v1.5.1
[1.5.0]: https://github.com/Hapfel1/er-save-manager/compare/v1.4.1..v1.5.0
[1.4.1]: https://github.com/Hapfel1/er-save-manager/compare/v1.4.0..v1.4.1
[1.4.0]: https://github.com/Hapfel1/er-save-manager/compare/v1.3.2..v1.4.0
[1.3.2]: https://github.com/Hapfel1/er-save-manager/compare/v1.3.1..v1.3.2
[1.3.1]: https://github.com/Hapfel1/er-save-manager/compare/v1.3.0..v1.3.1
[1.3.0]: https://github.com/Hapfel1/er-save-manager/compare/v1.2.2..v1.3.0
[1.2.2]: https://github.com/Hapfel1/er-save-manager/compare/v1.2.1..v1.2.2
[1.2.1]: https://github.com/Hapfel1/er-save-manager/compare/v1.2.0..v1.2.1
[1.2.0]: https://github.com/Hapfel1/er-save-manager/compare/v1.1.0..v1.2.0
[1.1.0]: https://github.com/Hapfel1/er-save-manager/compare/v1.0.0..v1.1.0
[1.0.0]: https://github.com/Hapfel1/er-save-manager/compare/v0.14.1..v1.0.0
[0.14.1]: https://github.com/Hapfel1/er-save-manager/compare/v0.14.0..v0.14.1
[0.14.0]: https://github.com/Hapfel1/er-save-manager/compare/v0.13.0..v0.14.0
[0.13.0]: https://github.com/Hapfel1/er-save-manager/compare/v0.12.1..v0.13.0
[0.12.1]: https://github.com/Hapfel1/er-save-manager/compare/v0.11.1..v0.12.1
[0.11.1]: https://github.com/Hapfel1/er-save-manager/compare/v0.11.0..v0.11.1
[0.11.0]: https://github.com/Hapfel1/er-save-manager/compare/v0.10.1..v0.11.0
[0.10.1]: https://github.com/Hapfel1/er-save-manager/compare/v0.10.0..v0.10.1
[0.10.0]: https://github.com/Hapfel1/er-save-manager/compare/v0.9.0..v0.10.0
[0.9.0]: https://github.com/Hapfel1/er-save-manager/compare/v0.8.0..v0.9.0
[0.8.0]: https://github.com/Hapfel1/er-save-manager/compare/v0.7.4..v0.8.0
[0.7.4]: https://github.com/Hapfel1/er-save-manager/compare/v0.7.3..v0.7.4
[0.7.3]: https://github.com/Hapfel1/er-save-manager/compare/v0.7.2..v0.7.3
[0.7.2]: https://github.com/Hapfel1/er-save-manager/compare/v0.7.1..v0.7.2
[0.7.1]: https://github.com/Hapfel1/er-save-manager/compare/v0.7.0..v0.7.1
[0.7.0]: https://github.com/Hapfel1/er-save-manager/compare/v0.6.2..v0.7.0
[0.6.2]: https://github.com/Hapfel1/er-save-manager/compare/v0.6.1..v0.6.2
[0.6.1]: https://github.com/Hapfel1/er-save-manager/compare/v0.6.0..v0.6.1
[0.6.0]: https://github.com/Hapfel1/er-save-manager/compare/v0.5.1..v0.6.0
[0.5.1]: https://github.com/Hapfel1/er-save-manager/compare/v0.5.0..v0.5.1
[0.5.0]: https://github.com/Hapfel1/er-save-manager/compare/v0.4.1..v0.5.0
[0.4.1]: https://github.com/Hapfel1/er-save-manager/compare/v0.4.0..v0.4.1
[0.4.0]: https://github.com/Hapfel1/er-save-manager/compare/v0.3.0..v0.4.0
[0.3.0]: https://github.com/Hapfel1/er-save-manager/compare/v0.2.1..v0.3.0
[0.2.1]: https://github.com/Hapfel1/er-save-manager/compare/v0.2.0..v0.2.1
[0.2.0]: https://github.com/Hapfel1/er-save-manager/compare/v0.1.0..v0.2.0

