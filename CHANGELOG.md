# 📜 ER Save Manager - Release History

> A comprehensive changelog for the Elden Ring Save Manager application.
> All notable changes to this project are documented here.

## 📦 Release 1.5.2
**Released:** June 29, 2026


### 🔧 Bug Fixes

- Correct consumable stack location and convergence upgrade caps (#193) ([ffe3465](https://github.com/Hapfel1/er-save-manager/commit/ffe34656fc52e868db4a312de6c88477c2387753))

- Correct inventory counter updates for key items in add/remove ([e85e039](https://github.com/Hapfel1/er-save-manager/commit/e85e039e280c829b5bfacfd0e295866af0787f16))

- Trigger auto-backup on every game launch, not once per session `[backup]` ([2ee638d](https://github.com/Hapfel1/er-save-manager/commit/2ee638d81dde2d5b92010aa5b21622cd414550ed))

- Rename invasion regions to unlocked regions ([2e9ed01](https://github.com/Hapfel1/er-save-manager/commit/2e9ed010e0ba6a6a60fdb1b077623a1959485c5e))

- Detect and repair corrupted inventory item counters in character details ([fe5aa9c](https://github.com/Hapfel1/er-save-manager/commit/fe5aa9c48d238bd3bb32e8299cdceee876ef8d72))

- Add Event Flag mapping for maps and ashes of war ([6ceba63](https://github.com/Hapfel1/er-save-manager/commit/6ceba634e8d19c8843648d5284388ad88ab5a9eb))



### 🎨 User Interface

- Add Video Guide button for Ghost's video guide ([74b6f1e](https://github.com/Hapfel1/er-save-manager/commit/74b6f1ec39493a91525cd1843ee0c87b9cda825b))



### 📦 Dependencies

- Bump the github-actions group with 2 updates `[deps]` ([91cc328](https://github.com/Hapfel1/er-save-manager/commit/91cc328aa490335a822f45aba863c78ba70635ee))



### Data

- Migrate icon storage from zip to sqlite, fix nexus mods quarantine ([10d42eb](https://github.com/Hapfel1/er-save-manager/commit/10d42eb7e64d403d2e0dcba3d603a44cf629b5a2))



---
## 📦 Release 1.5.1
**Released:** June 23, 2026


### 🔧 Bug Fixes

- Update player_game_data_offset after gaitem shift and bump mm level on weapon spawn ([9f45343](https://github.com/Hapfel1/er-save-manager/commit/9f45343cd8b5be206a1fae22414eb608169350ee))

- Auto-adjust matchmaking level on weapon removal, remove manual set button ([a8d1a20](https://github.com/Hapfel1/er-save-manager/commit/a8d1a20aa6da0b69703f5017b1cba0f6a5288d36))

- Added missed Convergence Item, Warding Remnant ([70fb917](https://github.com/Hapfel1/er-save-manager/commit/70fb9174eb358d568002e3f366485b2ffdc4d7b7))

- Add boss status dialog, fix bell bearing NG+ flags, fix search debounce (closes #189) ([ed0afb2](https://github.com/Hapfel1/er-save-manager/commit/ed0afb2422e89c427f80e59ecacd8f552b1e861e))

- Prevent integer overflow from corrupted acquisition indices `[inventory]` ([5c4f935](https://github.com/Hapfel1/er-save-manager/commit/5c4f93559df8b0623a4a1a6815972112aac6b9eb))

- Adjust UI spacing and resolve loadout file path `[inventory]` ([19aa279](https://github.com/Hapfel1/er-save-manager/commit/19aa279dadb2f6c8e147455340ac79d871a3844f))



### 🎨 User Interface

- Made CSNetMan.bin replace button show permanently ([2486af1](https://github.com/Hapfel1/er-save-manager/commit/2486af1d4590d0dc298e24b764eb6361b06ed2b0))

- Made Message about CsNetMan more clear ([902dfdb](https://github.com/Hapfel1/er-save-manager/commit/902dfdba6c2fa1aa27dacbc986db068a051dfd92))

- Add Debug warped face button ([a43e5df](https://github.com/Hapfel1/er-save-manager/commit/a43e5dfa46aa66c9b0632bad5f5284d53e23f17b))

- Add loadout manager, batch spawning, and smart stacking `[inventory]` ([10d3f93](https://github.com/Hapfel1/er-save-manager/commit/10d3f9300cc62897b4f757b6872f698d174925ef))

- Replace warped face button with slider dialog for secondary face deformation ([b13fbe7](https://github.com/Hapfel1/er-save-manager/commit/b13fbe767a57f131f812e1bc37896ea9c465ca5c))



### ♻️ Code Refactoring

- Remove CSNetMan replace button toggle setting ([92744b0](https://github.com/Hapfel1/er-save-manager/commit/92744b046a41219369a8c7c6f859581148ae2420))



### 📦 Dependencies

- Bump the github-actions group with 3 updates `[deps]` ([ea4b49e](https://github.com/Hapfel1/er-save-manager/commit/ea4b49ea31f40e5fca10ff0939d9c5d8c5c24f6e))



### 🧹 Maintenance

- Migrate nexusmods upload action to v1.0.0-beta.8 ([10d8f67](https://github.com/Hapfel1/er-save-manager/commit/10d8f67e5ddabc916eb276cbbf3128c98165a46d))



---
## 📦 Release 1.5.0
**Released:** June 18, 2026


### ✨ New Features

- Add Nightreign save editor `[NR]` ([6df3ac9](https://github.com/Hapfel1/er-save-manager/commit/6df3ac9f5eb5ffe963d9d02fff76860795d613b2))

- Add 3.0 update support `[convergence]` ([80150b5](https://github.com/Hapfel1/er-save-manager/commit/80150b59ba03666b87c57d54845fca949ace8f3b))



### 🔧 Bug Fixes

- Fix relics tab layout in fixed-height window `[NR]` ([00d8947](https://github.com/Hapfel1/er-save-manager/commit/00d89476735d5a7e24f6afd0c5ee97a72931ba84))

- Removed cut content cookbooks ([b087ab6](https://github.com/Hapfel1/er-save-manager/commit/b087ab6b5b3fd087c183702d876289583e71dd4c))

- Cookbook/whetblade event flags and display fixes `[inventory]` ([66dff69](https://github.com/Hapfel1/er-save-manager/commit/66dff6924939d1d5312492b14ffc4e0180482f3e))

- Expand _KEY_ITEM_BASE_IDS with all confirmed key item categories `[inventory]` ([7ab5a30](https://github.com/Hapfel1/er-save-manager/commit/7ab5a30b4fdffed63e7b09d9daa7da612bcaa3ea))

- Remove cut content and fix item names across goods CSVs `[items]` ([b868b39](https://github.com/Hapfel1/er-save-manager/commit/b868b39ae027a26ad3ed20089758257e2e38d7ae))

- Add containers and upgrade items to _KEY_ITEM_BASE_IDS `[inventory]` ([610e822](https://github.com/Hapfel1/er-save-manager/commit/610e822f1eb92a5bb0191697b1d6c7da3022d59f))

- Add Dragon Heart and Lost Ashes of War to _KEY_ITEM_BASE_IDS `[inventory]` ([36b3d8b](https://github.com/Hapfel1/er-save-manager/commit/36b3d8baf534ae271154e83694ee3a40f5822702))

- Remove two cut content items ([5e13a5d](https://github.com/Hapfel1/er-save-manager/commit/5e13a5dc32241b4e367add5fd1054785c745593d))



### 🎨 User Interface

- Ui: Fixed Icons being the same for modified variants of certain Items:
Lord of Blood's Favor
Unalloyed Gold Needle
Miniature Ranni
Academy Glintstone Key
Larval Tear ([536fa62](https://github.com/Hapfel1/er-save-manager/commit/536fa62e8a3d0e69eaab070455b93d6920deb6df))

- Replace pruning warning with pre-deletion CTk dialog `[backup]` ([2c9828b](https://github.com/Hapfel1/er-save-manager/commit/2c9828b737887edcbd9a61c4bbe7cbacaf23d3b9))



### 📦 Dependencies

- Bump taiki-e/install-action in the github-actions group `[deps]` ([766486c](https://github.com/Hapfel1/er-save-manager/commit/766486c604394572e3bcaabf3a08bef902ecc418))



---
## 📦 Release 1.4.1
**Released:** June 09, 2026


### 🔧 Bug Fixes

- Ashes Name Resolution, Allow Duplicate Talismans, Fix Melee filter exlcuding infused weapons in visual inventory ([54c9742](https://github.com/Hapfel1/er-save-manager/commit/54c97424d0cb4f7f60413ca89f85af37f4294706))

- Removed "No Presets" warning as this is not needed anymore and is possible now ([53bb5e7](https://github.com/Hapfel1/er-save-manager/commit/53bb5e77000ff4dafde6c2fae3171e0d343c9b08))

- Fix incorrect starting class ID assignment #169 ([b34f070](https://github.com/Hapfel1/er-save-manager/commit/b34f07040a00cb61fc07d76324e246b09f90bd80))

- Enforce class stat minimums in stats editor, notify on archetype change ([806f742](https://github.com/Hapfel1/er-save-manager/commit/806f7427fe2d87ed10b5c66161912680dd97cbbd))

- Correct wrong IDs for 8 ashes in Ashes.csv and DLCAshes.csv #170 ([b0d9c70](https://github.com/Hapfel1/er-save-manager/commit/b0d9c70d728fd90ccec56f5c001c971c50e59df1))

- Correct body type encoding, NPC alive/dead offset handling `[DSR]` ([b4a7c4d](https://github.com/Hapfel1/er-save-manager/commit/b4a7c4d70642498822785ce180ea739f019ccf58))

- Match gems in gaitem map by base_id via handle prefix ([aa71552](https://github.com/Hapfel1/er-save-manager/commit/aa71552df77d5ed5ace830f2d684a295f41184d8))

- Hide PS button for non-ER games, fix item gib DS3 nav, restore SteamID tab position on PC save reloadfix: hide PS button for non-ER games, fix item gib DS3 nav, restore SteamID tab position on PC save reload ([6d8a3e2](https://github.com/Hapfel1/er-save-manager/commit/6d8a3e2282342e51bcb26fc0fdc68aa2419cbe92))

- Mirror gaitem handle second byte from save; add held→storage fallback ([9b05cfd](https://github.com/Hapfel1/er-save-manager/commit/9b05cfdbba7eecdd16e5c955ce3daaa77c06adea))

- Redo Item DB by getting data from Params ([722501a](https://github.com/Hapfel1/er-save-manager/commit/722501ae6ea4330aef7296a5e94e97195af45756))

- Match gem gaitem by base_id or full_item_id ([63edea5](https://github.com/Hapfel1/er-save-manager/commit/63edea5f15145fd65a1083d7a7faf570b462d829))

- Fix weapon spawn `[DS3]` ([0ddffc4](https://github.com/Hapfel1/er-save-manager/commit/0ddffc445c4ad1b24451767f8a24adcaf8e87f02))

- Accept more formats in the appearance tab JSON import ([5bc098a](https://github.com/Hapfel1/er-save-manager/commit/5bc098aa55f18749103853c424407eb75f6c521b))

- Potential PS fix for spawning weapons ([fdc0d52](https://github.com/Hapfel1/er-save-manager/commit/fdc0d524061e2c81a2adf6126c5a608166f10887))

- Read second byte from first gaitem entry and reuse it for all spawned handle ([3018686](https://github.com/Hapfel1/er-save-manager/commit/3018686fc036913a572a0c06d58e9db42e5ab140))

- Default UI scale to 100% instead of Auto ([e816c9f](https://github.com/Hapfel1/er-save-manager/commit/e816c9fe802f8bbb33084962dab7f911a5cfade9))

- Lazy-load preset thumbnails in background threads ([e1f1388](https://github.com/Hapfel1/er-save-manager/commit/e1f1388b9f3a39a4681ccd3af70a2e97944ded59))



### 🎨 User Interface

- Added Display Scale Setting ([69f462f](https://github.com/Hapfel1/er-save-manager/commit/69f462f37d2d44ee65358af5df02b0667fb35806))

- Add 104 NPC appearance presets to the preset browser ([6b07f97](https://github.com/Hapfel1/er-save-manager/commit/6b07f97f1732a749a758d572e1e1f58f3eabe0ac))



### 📦 Dependencies

- Bump the github-actions group with 3 updates `[deps]` ([4c838e8](https://github.com/Hapfel1/er-save-manager/commit/4c838e84ede334d78e712c2a588dd5464a1dbe16))



---
## 📦 Release 1.4.0
**Released:** June 04, 2026


### ✨ New Features

- Added PlayStation Save File Reading and Editing `[ER]` ([41d87d7](https://github.com/Hapfel1/er-save-manager/commit/41d87d7eadd6dd118d6991ad34c191741d6b9686))

- Add DS3 save file editor module `[DS3]` ([132de69](https://github.com/Hapfel1/er-save-manager/commit/132de699b663bd5937d13fca7960d539cc20a3d8))



### 🔧 Bug Fixes

- Preserve global array header when writing to preset slot 0 ([d78675f](https://github.com/Hapfel1/er-save-manager/commit/d78675f2f5381ae3c57557d8f3bd6acc192dbef4))

- Added mising Convergence Item, Putrid Key ([0a88729](https://github.com/Hapfel1/er-save-manager/commit/0a88729158aa2439d189af2ac8733fbf35bb68cf))

- Route key items to key_items[] in inventory ops ([5c99b64](https://github.com/Hapfel1/er-save-manager/commit/5c99b6488ad0ba0eb650d436032836db5aaaa634))

- Skip checksum prefix on PS saves for all slot writes ([a9069dd](https://github.com/Hapfel1/er-save-manager/commit/a9069dd3b5976e14f9658f2e2ee7a0024b20f06f))

- Correct event flag base offset, add level recalc, flag lookup tab `[DSR]` ([64200f4](https://github.com/Hapfel1/er-save-manager/commit/64200f42a85a5974bcc9d7b3381f551adcca74b7))



### 🎨 User Interface

- Fix scroll bar bug in Icon Browser ([196da49](https://github.com/Hapfel1/er-save-manager/commit/196da49a1176fdf0e1bd5ca1c7df3d186e7ada0d))

- Rewrite info text to adjust for Switch and Playstation saves ([9ce410a](https://github.com/Hapfel1/er-save-manager/commit/9ce410a804785fafe89b99620117d88b892cc769))



### 📦 Dependencies

- Bump the github-actions group with 2 updates `[deps]` ([93bf07e](https://github.com/Hapfel1/er-save-manager/commit/93bf07e25a4ffe760c6a2ae1c09fb202731af842))



---
## 📦 Release 1.3.2
**Released:** May 29, 2026


### ✨ New Features

- Add DS3 save file editing `[DS3]` ([0bb980c](https://github.com/Hapfel1/er-save-manager/commit/0bb980c381e54df813ed6b95ff0bfbcc4af7e96f))

- Add Item Spawning `[DS3]` ([fd4960f](https://github.com/Hapfel1/er-save-manager/commit/fd4960fe3201e12a221c5291df207b487becc784))



### 🔧 Bug Fixes

- Fixed some convergence weapons having affinity options when they should not have them ([8e60b4a](https://github.com/Hapfel1/er-save-manager/commit/8e60b4a265b4b5ce8deaaef0c6869613dd14112f))

- Added probing to find correct inventory size ([8b80f93](https://github.com/Hapfel1/er-save-manager/commit/8b80f93f0fc1d19b8c91c614b2859a6dbcee3e4a))

- Added missed SeamlessCoop Item (Crimson Blossom) `[DSR]` ([81ec6cc](https://github.com/Hapfel1/er-save-manager/commit/81ec6cc9f3418e5ed647f0a08b5b5ba7252939e0))

- Added missing Attribute level validation ([8171902](https://github.com/Hapfel1/er-save-manager/commit/8171902c05f167135781e2253f8c6eeaf338d586))



### 🎨 User Interface

- Redid character transferring between files flow to make it more user friendly ([a8087f5](https://github.com/Hapfel1/er-save-manager/commit/a8087f53a4015467f284594d922f2ee16173556f))

- Add info about quest steps that stay applied even after fully resetting quest progress ([180d876](https://github.com/Hapfel1/er-save-manager/commit/180d87650f9b6b569dc04ab868b1f5f4cefe38eb))

- Added SeamlessCoop Items for DSR ([70fa936](https://github.com/Hapfel1/er-save-manager/commit/70fa936c2241aa28e1bd5c9861c4829fe8b923e2))

- Added setting to disable "Save File modified externally" warning ([30256c4](https://github.com/Hapfel1/er-save-manager/commit/30256c47c309e0c84a5219f43cb1075fb44ddc61))

- Fixed Search Indexing Bug in Icon Browser ([1f8a5b6](https://github.com/Hapfel1/er-save-manager/commit/1f8a5b62be0ca4aa3bf17066a51d105838cfc5e0))

- Remove unnecessary popup when editing stats and also instantly change the level total in CSProfileSummary when total level changes ([fdb3188](https://github.com/Hapfel1/er-save-manager/commit/fdb3188c73518bc7c493c03871b7fa44eae8d23e))



---
## 📦 Release 1.3.1
**Released:** May 26, 2026


### 🔧 Bug Fixes

- Added missed Convergence Items (Maps and Perfumer quest items) ([94940cf](https://github.com/Hapfel1/er-save-manager/commit/94940cf8aab71cba06af0c8d6270eb2b7bf95cf6))

- Fixed issue with interpreting int level making it unable to apply NG+7 ([d33e24e](https://github.com/Hapfel1/er-save-manager/commit/d33e24e63c234705a7d36af09b48f07190d6ddee))

- Fixed build issue ([8fdbf21](https://github.com/Hapfel1/er-save-manager/commit/8fdbf211dddfefb55752a30049c2171544c6ffcd))

- Write CSNetMan.bin at net_man_offset - 4 `[netman]` ([f999aa9](https://github.com/Hapfel1/er-save-manager/commit/f999aa9f83350d86ed9a2378c6a0c13026fec26a))

- Fully implemented Affinity/Gem Validation for Convergence Saves ([8280c43](https://github.com/Hapfel1/er-save-manager/commit/8280c43a48a0f822888500f93a3e3302c64559cc))



### 🎨 User Interface

- Add .cnv to the browse option filter ([a27c3d7](https://github.com/Hapfel1/er-save-manager/commit/a27c3d7745d11642e4ccae226ca267cf5dd41a6e))

- Fixed "Save File has been modified externally" popping up after modifying the save file with the manager ([7d630e3](https://github.com/Hapfel1/er-save-manager/commit/7d630e3d0c7af31dd860144b90e120fc67e56c13))



### 📦 Dependencies

- Bump taiki-e/install-action in the github-actions group `[deps]` ([ff829da](https://github.com/Hapfel1/er-save-manager/commit/ff829dacb7b04bf987e10c5360ed29b46eabebbe))



---
## 📦 Release 1.3.0
**Released:** May 22, 2026


### ✨ New Features

- Add DSR Save Editing: Stats Editor, Inventory Editor, NPC&Boss Revival, World State ([acc98e1](https://github.com/Hapfel1/er-save-manager/commit/acc98e154c2ae3b0451d74c9ab698c3165925992))

- Added Summoning Pool Button to the event flags tab to disable and enable summoning pools ([d2a56a2](https://github.com/Hapfel1/er-save-manager/commit/d2a56a2f6bcecdc7f618a8153c558611915437cb))



### 🔧 Bug Fixes

- Removed cut magic ([600cf03](https://github.com/Hapfel1/er-save-manager/commit/600cf0325bce17f9019cf3568eaa906e437db3c9))

- Added early return for a guard that caused a crash ([b116508](https://github.com/Hapfel1/er-save-manager/commit/b1165087382a6be8be8874e0df19283d6bbba321))



### 🎨 User Interface

- Add new popup when a loaded save file gets modified externally ([b69ecdc](https://github.com/Hapfel1/er-save-manager/commit/b69ecdceadfa3e6e152c2a5961357251676cf5de))

- Improve DSR tabs `[DSR]` ([c85c66f](https://github.com/Hapfel1/er-save-manager/commit/c85c66fe42cc3bfb0c582a8099d459b13fb26033))

- Add missing Convergence Armor ([ecbb2ca](https://github.com/Hapfel1/er-save-manager/commit/ecbb2caf7e9a09d3eedf4183ecd3c46a8131ab63))



---
## 📦 Release 1.2.2
**Released:** May 19, 2026


### 📦 Dependencies

- Bump taiki-e/install-action in the github-actions group `[deps]` ([af11b51](https://github.com/Hapfel1/er-save-manager/commit/af11b51c1a69038814eca7c17fc432a69bcf4ec7))



---
## 📦 Release 1.2.1
**Released:** May 14, 2026


### 🔧 Bug Fixes

- Inventory update operations and crashing issue ([1c8081e](https://github.com/Hapfel1/er-save-manager/commit/1c8081e5eda7844b44b0474c7c7f4ce3d1827130))

- Fixed Convergence IDs that collided with base game IDs overwriting base game item names on non convergence saves ([3c65c8f](https://github.com/Hapfel1/er-save-manager/commit/3c65c8fbca94a7c1d6236cb64195c1f9ed0b3fef))

- Fixed icon display issues, updated database ([035e717](https://github.com/Hapfel1/er-save-manager/commit/035e717b608f767f61a3bd0106484575d8509838))

- Fix nyasu import to correctly import talisman pouches and memory slots ([504b6e1](https://github.com/Hapfel1/er-save-manager/commit/504b6e1f471902fe78fa5e8c7c86431d1c9a2e42))



### 🎨 User Interface

- Added view as icons for all items to make it  more user friendly ([3086051](https://github.com/Hapfel1/er-save-manager/commit/3086051271fe8e94d94249a5fd7851bb77b84f03))

- Added Visual Inventory ([a2d0ae7](https://github.com/Hapfel1/er-save-manager/commit/a2d0ae71ef70e910edd062c177e3b60b8ca885bd))

- Added full visual Item Picker ([ccb68f3](https://github.com/Hapfel1/er-save-manager/commit/ccb68f3fea3d7cf2b2ea294d904341863851b13c))

- Increased Font Size and centered all new popups ([b4f505e](https://github.com/Hapfel1/er-save-manager/commit/b4f505e5281b3632b3aa06240e4c1d7563ed5e7b))



---
## 📦 Release 1.2.0
**Released:** May 12, 2026


### ✨ New Features

- Added more modification to existing items in inventory (set affinity, aow, upgrade level) with the correct validation ([5caafc4](https://github.com/Hapfel1/er-save-manager/commit/5caafc43fbf1337de1996e8c912034898a5f2a8c))



### 🔧 Bug Fixes

- Fixed unkown item ids showing up ([f950bb7](https://github.com/Hapfel1/er-save-manager/commit/f950bb7078a53152ee6cec9a548a99a6b8fa9caf))

- Fixed Weapon mm level calculation ([6a24869](https://github.com/Hapfel1/er-save-manager/commit/6a24869dd3073319e9b02d29a9893ccd698c820f))

- Correct EF tear false positive and remove unreliable anchor override `[deep_scan]` ([508e170](https://github.com/Hapfel1/er-save-manager/commit/508e1708a717ec9d627a5518570e68fddb469bf4))

- Fix update inventory ops with rebuild to fix crashing issue

Co-authored-by: Copilot <copilot@github.com> ([24a31f3](https://github.com/Hapfel1/er-save-manager/commit/24a31f3272b9b284a6ac578b79ae714873baeb81))

- Improve Item Spawning to avoid crashing/corruption ([210fb35](https://github.com/Hapfel1/er-save-manager/commit/210fb356a1a3c926d0c1e74f8ab4f98d48b11e70))

- Fixed Item Import and slot rebuild to cause more corruption issues ([d04eb45](https://github.com/Hapfel1/er-save-manager/commit/d04eb457f9597f868356acd8e7f5b58edbfaf99a))

- Add maxrepositorynum ([d3c48a9](https://github.com/Hapfel1/er-save-manager/commit/d3c48a9563226e6a929aa34674d249d04a4135af))



### 🎨 User Interface

- Add ItemGib button ([8c6c26f](https://github.com/Hapfel1/er-save-manager/commit/8c6c26fe9e6bbdbc81a8c4a417e4917ebb98c388))



### 📦 Dependencies

- Bump taiki-e/install-action in the github-actions group `[deps]` ([2811c8f](https://github.com/Hapfel1/er-save-manager/commit/2811c8f8a3dcd8e55389e29575d31ef8ee7449ba))



---
## 📦 Release 1.1.0
**Released:** May 04, 2026


### ✨ New Features

- Structured item data with param validation `[inventory]` ([c12b807](https://github.com/Hapfel1/er-save-manager/commit/c12b807956fdd4a2020ac95a529af0516e98b9f5))



### 🔧 Bug Fixes

- Remove_item was ignoring the delta return value so it did not shift the offsets correctly ([69dfc16](https://github.com/Hapfel1/er-save-manager/commit/69dfc164741a189275ccae21061aedcc2ca3b652))

- Converted Database files to csv, added more params to validate each spawned item, split up add_item function ([b29471a](https://github.com/Hapfel1/er-save-manager/commit/b29471aad7755d10a0e1ac3219e13435b185bb19))



### 📦 Dependencies

- Bump taiki-e/install-action in the github-actions group `[deps]` ([ae6993d](https://github.com/Hapfel1/er-save-manager/commit/ae6993dd0f3e679ba703f579b245e375ea1f54f7))



---
## 📦 Release 1.0.0
**Released:** May 03, 2026


### ✨ New Features

- Added Item Spawning ([7141e3f](https://github.com/Hapfel1/er-save-manager/commit/7141e3ff19ad5efce917ef9577435a968843088d))

- Release v1.0.0 ([9d2ff22](https://github.com/Hapfel1/er-save-manager/commit/9d2ff228d4d5c18bfc1cc38c2f5a38f92c6912b9)) ⚠️ **BREAKING CHANGE**



### 🔧 Bug Fixes

- Fixed deep scan issues ([98ac717](https://github.com/Hapfel1/er-save-manager/commit/98ac717f50c134dd2c55df1c27548179cb531b90))



### 📦 Dependencies

- Bump taiki-e/install-action in the github-actions group `[deps]` ([d6fd9be](https://github.com/Hapfel1/er-save-manager/commit/d6fd9bec7902a586653d202884cf8e5c3935a219))



---
## 📦 Release 0.14.1
**Released:** April 22, 2026


### 🔧 Bug Fixes

- Add replacenetman option and button for trashed csnetmans without visible write torns ([44075f5](https://github.com/Hapfel1/er-save-manager/commit/44075f5229e9f16bf2314ca1927b8f348f817e5a))

- Fixed steamid not being synced correctly when importing from a .erc file ([6f7f3fa](https://github.com/Hapfel1/er-save-manager/commit/6f7f3fa2590c95919f102b258bfd00f09adff770))



### 🎨 User Interface

- Add import flags button and add "All" selection for event flag categories with subcategories ([ed9b36c](https://github.com/Hapfel1/er-save-manager/commit/ed9b36c2aa0cbb45a9cb046d2131f85ea933fd5b))

- Added Playtime Editor ([6bf0805](https://github.com/Hapfel1/er-save-manager/commit/6bf080529b49a86893d2ace6ffb121ba67d2c371))



### 📦 Dependencies

- Bump the github-actions group with 2 updates `[deps]` ([6639df2](https://github.com/Hapfel1/er-save-manager/commit/6639df2b1985f73f8984926bd24f5f536b43e0e5))

- Bump the github-actions group with 2 updates `[deps]` ([7f7c08c](https://github.com/Hapfel1/er-save-manager/commit/7f7c08ca2cfc4943a833ce622f8aae1bdf6aa0a2))



---
## 📦 Release 0.14.0
**Released:** April 10, 2026


### 📦 Dependencies

- Bump taiki-e/install-action in the github-actions group `[deps]` ([3ba7626](https://github.com/Hapfel1/er-save-manager/commit/3ba76262255cd967250d33bf44582ea42a0702dc))



---
## 📦 Release 0.13.0
**Released:** April 02, 2026


### ✨ New Features

- Added Invasion Regions and ingame settings ([1b1097b](https://github.com/Hapfel1/er-save-manager/commit/1b1097bd7bae370995f0dec1cdeb10db9f1450f2))

- Add other Fromsoft Games for SteamID Patching and Backup Manager ([fc2a616](https://github.com/Hapfel1/er-save-manager/commit/fc2a616e832a9d7883aea56f733347ffa2b2d3a4))

- Added "Move Bloodstain to player" button in the world state tab ([48cd065](https://github.com/Hapfel1/er-save-manager/commit/48cd0650e40adc9ac90634a1c7e214e2918dedba))

- Add weapon_matchmaking_level and a check for every weapon upgrade level to combat any tries to abuse modifying it ([f68ac2f](https://github.com/Hapfel1/er-save-manager/commit/f68ac2fe3eb5b2402921ded78bf5b314ba361e10))

- Added Item Spawning ([eaceae8](https://github.com/Hapfel1/er-save-manager/commit/eaceae82ab9ca165e35b5b84b43b4ffc36383c12))

- Added Equipment Editing ([47893cb](https://github.com/Hapfel1/er-save-manager/commit/47893cb9c19d1ff55b7ce2dc84e5288498c187d8))



### 🔧 Bug Fixes

- Fix event flag custom id toggle not creating backups ([74d7434](https://github.com/Hapfel1/er-save-manager/commit/74d7434b17a3130271cef01903ce5afeddcd74b3))

- Fixed rendering issue in Appearance Tab popup window ([fb7b38b](https://github.com/Hapfel1/er-save-manager/commit/fb7b38bcd29fe9f81d9b31ef64bc502a3e6efc08))

- Added change files ([ea91317](https://github.com/Hapfel1/er-save-manager/commit/ea913171336039d22620c44c0f6b8af4c82e0bfe))

- Lint ([188f267](https://github.com/Hapfel1/er-save-manager/commit/188f267955f123b87c7ff06aea53f1fc13706861))

- Added correct functionality for steamid patching for each game ([d266428](https://github.com/Hapfel1/er-save-manager/commit/d266428169e8aaec34f642098e990b2508d05c91))

- Fixed Save Loading and Process detection for Non-ER games ([1ca1b68](https://github.com/Hapfel1/er-save-manager/commit/1ca1b68aa2d2c605eb00bf583e8410822e3e7c21))

- Fixed SteamID auto-detection on Linux ([7e2ee39](https://github.com/Hapfel1/er-save-manager/commit/7e2ee39acfe73cee08912268298f3929a9994db5))

- Fixed Steam vanity link parsing ([46458e7](https://github.com/Hapfel1/er-save-manager/commit/46458e79b78f6f6aeeb970cfdd70e858d22cb631))

- Fix Open folder button on certain Linux distros not working ([5617f65](https://github.com/Hapfel1/er-save-manager/commit/5617f65e2d3eb1088f81b206b04837cae1923e19))

- Fixed the upgrade level detection ([96ab048](https://github.com/Hapfel1/er-save-manager/commit/96ab048d629d5a89906fd509ff88c93f42398100))

- Fixed process monitoring ([9aaabfb](https://github.com/Hapfel1/er-save-manager/commit/9aaabfb738f12b62f326031c1965aabcbf004290))

- Fixed process detection for is_game_running ([4b57a80](https://github.com/Hapfel1/er-save-manager/commit/4b57a8013d422c224e2e24369972357c62adf738))

- Fixed character name not being read correctly because of garbage data ([df34500](https://github.com/Hapfel1/er-save-manager/commit/df3450088e16adbe1850891a850af76edccd9209))

- Format and lint ([9f5fd3a](https://github.com/Hapfel1/er-save-manager/commit/9f5fd3ad318d6f37da0b40c267e08ea5912d4d1c))

- Fixed png issue with character browser and impoved loading in the browser ([ffa3e96](https://github.com/Hapfel1/er-save-manager/commit/ffa3e9654a13f23a46ff7d9bc3d5bbf810a79dc8))

- Fixed cpu0 feature not applying correctly ([242cf46](https://github.com/Hapfel1/er-save-manager/commit/242cf4693b911cd4ca904cf53a9635e883158279))

- Lint ([fbdba81](https://github.com/Hapfel1/er-save-manager/commit/fbdba8108e8937d5fa9a3ff0a91fde86a7e1b323))

- Fixed equipment editor not creating backups ([04198a2](https://github.com/Hapfel1/er-save-manager/commit/04198a2c75c4014d6c8575a620452f981f00fd06))



### 🎨 User Interface

- Add Event Flag Export ([9e82142](https://github.com/Hapfel1/er-save-manager/commit/9e82142a1ebf7c08292d411f123a5ef2afb2fdf5))

- Added Great Rune and Rune Arc display ([16bf210](https://github.com/Hapfel1/er-save-manager/commit/16bf210aa3a11d93d8a3185d9abe9b6440eb1e93))

- Fixed popup centering ([ad7d66a](https://github.com/Hapfel1/er-save-manager/commit/ad7d66ad1dea14bd07190e9a667fd295de496927))

- Added warning when no apperance presets are saved to first save one in game ([62bcefa](https://github.com/Hapfel1/er-save-manager/commit/62bcefa5f3c89c7a960ff5d735351f407ec37f1f))

- Add MapID map for the known locations teleport feature ([24d95be](https://github.com/Hapfel1/er-save-manager/commit/24d95be71c1b4264a8b5a32c307cca6fdf4aa910))

- Add "Apply CPU 0 fix on game launch" setting for ER, NR and DS3 ([e4654b4](https://github.com/Hapfel1/er-save-manager/commit/e4654b4f258ba0f028b0622e41a47e1e57beb3f6))

- Fix performance issues ([e1c2ae0](https://github.com/Hapfel1/er-save-manager/commit/e1c2ae012e18ce647991d119e74dd50b0c856af3))

- Rework vanilla save warning ([5faf9f6](https://github.com/Hapfel1/er-save-manager/commit/5faf9f6be829ce2b82f9bc6d8ef8e61abbbddfda))

- Remade Inventory Editor UI and added Affinities ([7fa65a7](https://github.com/Hapfel1/er-save-manager/commit/7fa65a71529f2228558459818ec04b15b521f454))



### 📦 Dependencies

- Bump the github-actions group with 3 updates `[deps]` ([e630f06](https://github.com/Hapfel1/er-save-manager/commit/e630f06a9675308963fedd3091a6be21d9bc2fbb))



### Buld

- Lint ([e759435](https://github.com/Hapfel1/er-save-manager/commit/e759435744f1e499aec4cd9f2c29ffaa57788bf7))



---
## 📦 Release 0.12.1
**Released:** March 23, 2026


### ✨ New Features

- Added Event Flag Torn Detection and Fix ([d535ea5](https://github.com/Hapfel1/er-save-manager/commit/d535ea5f2922da4ce3ab2a3a555490f5deb64350))



### 🔧 Bug Fixes

- Fixed last opened save location not working on Linux ([b65a1da](https://github.com/Hapfel1/er-save-manager/commit/b65a1dabc913e232b3ff85de87833bf9b692367b))

- Add netman validation and corruption fixing after byteshift ([7405b3d](https://github.com/Hapfel1/er-save-manager/commit/7405b3d7a9fe25c278ef191803786ea3f99de70e))

- Fixed dlc flag detection + added apply button when only checking that checkbox ([f6ed165](https://github.com/Hapfel1/er-save-manager/commit/f6ed16569fef75e41dad2b3700fbf54d0a091f76))

- Added Checksum validation for slots ([adebcb8](https://github.com/Hapfel1/er-save-manager/commit/adebcb81b14bef64c57874a2255508add9d7d391))

- Added event flags for npc quests and a tab for checking progress ([03ebe4b](https://github.com/Hapfel1/er-save-manager/commit/03ebe4ba6b601b4cae4f19c9b633bfdc226125b6))



### 🎨 User Interface

- Add button that links to discord server ([12ff6bc](https://github.com/Hapfel1/er-save-manager/commit/12ff6bcfc1c82ab2ac48fa3dd171ab719cd736c9))

- Made popups from character_details appear centered over its parent ([9a814f2](https://github.com/Hapfel1/er-save-manager/commit/9a814f206157460adad1e895473d779e861b7afa))



### 📦 Dependencies

- Bump the github-actions group with 2 updates `[deps]` ([285e359](https://github.com/Hapfel1/er-save-manager/commit/285e35912bb1c8b9f301a4f8bbdbb319cddfad34))

- Bump taiki-e/install-action in the github-actions group `[deps]` ([5bb543f](https://github.com/Hapfel1/er-save-manager/commit/5bb543fc3c2f6b0088cfd4596e0fa6f54e0d820c))



---
## 📦 Release 0.11.1
**Released:** March 14, 2026


### 🔧 Bug Fixes

- Fix: use data_start consistently
fbcbdc3 converted the offsets from slot-relative to absolute, but only
in the slot itself - all of the other scripts still expected it to have
been removed and would re-add the slot data offset back in, corrupting
the pointer and trashing the save slot. This removes the slot offset
addition from all of the places where the slot data offset is already
present in the slot object itself, preventing corruption ([e62ae60](https://github.com/Hapfel1/er-save-manager/commit/e62ae60ec290e7e5b8e5242e8997eada664235ce))

- Fixed offsets being applied twice ([058008f](https://github.com/Hapfel1/er-save-manager/commit/058008f4c65b237da0546b710095363ba64b851f))



---
## 📦 Release 0.11.0
**Released:** March 13, 2026


### ✨ New Features

- Add NPC respawner ([a6cb90d](https://github.com/Hapfel1/er-save-manager/commit/a6cb90dfbae0e38e69f3f3ff3b39f5140560b9f2))

- Added known locations to the World State Tab for teleporting ([2fba405](https://github.com/Hapfel1/er-save-manager/commit/2fba40548923b0d50fd6f8d45f233c24a791d654))

- Added more save file corruption detection and Fixes ([fbcbdc3](https://github.com/Hapfel1/er-save-manager/commit/fbcbdc31c7f17a6af4f214bb088e9e9cd6dae4b3))



### 🔧 Bug Fixes

- Fixed window popup render issue on linux ([8d340db](https://github.com/Hapfel1/er-save-manager/commit/8d340db0e9f52e6c4a586bc348df90dfe2bade46))

- Fixed SteamID Patcher AutoDetection ([57b1946](https://github.com/Hapfel1/er-save-manager/commit/57b19469d3092f3f5308babde7ae79a0046be3e8))

- Fixed scrolling on Linux ([a593c17](https://github.com/Hapfel1/er-save-manager/commit/a593c17a46f044fd6670c5bbd6243722cd2a2058))

- Fixed Character Operations also copying ProfileSummary so that the character gets shown correctly instantly ([1d8ef3f](https://github.com/Hapfel1/er-save-manager/commit/1d8ef3fbda28756713520490fc4bfd0ed48066a4))



### 🎨 User Interface

- Made game running detection more clear and added a button to force quit the game ([aad25ef](https://github.com/Hapfel1/er-save-manager/commit/aad25ef2d4671daa6e1d414821aecb05f0ecc520))

- Added new Toast info boxes to remove popup spam ([d3acb7b](https://github.com/Hapfel1/er-save-manager/commit/d3acb7bb2e41bc79d93ceb0e0447d52590296f7f))

- Remade Troubleshooting button to offer an Addon install for the standalone troubleshooter ([a71b5f0](https://github.com/Hapfel1/er-save-manager/commit/a71b5f0e7394f662e44ff36d1cdbe88ed233973b))

- Changed some info popups to be Toast notifications instead for a better UX ([02dfa6a](https://github.com/Hapfel1/er-save-manager/commit/02dfa6a283c0934ab07c3499168e10c58f8ef42b))

- Added character names next to the slot selections everywhere ([f52c46b](https://github.com/Hapfel1/er-save-manager/commit/f52c46b30f134fc5584cf516b2e7ced46fa6c7bb))



---
## 📦 Release 0.10.1
**Released:** February 11, 2026


### 🔧 Bug Fixes

- Fix : fix character ops error ([05df73c](https://github.com/Hapfel1/er-save-manager/commit/05df73cdb79e96d7e9d74a7e772746b3056cf51d))



---
## 📦 Release 0.10.0
**Released:** February 10, 2026


### ✨ New Features

- Added Auto-Backup Feature when booting up the game, changed backups to be zipped by default. ([992ed82](https://github.com/Hapfel1/er-save-manager/commit/992ed82a22d7cd62d1cb9330b64e93f134370a41))

- Added Character Browser ([c78dfe0](https://github.com/Hapfel1/er-save-manager/commit/c78dfe0068022e10b62408771378ee30e9879764))

- Add Convergence Support for the Character Browser ([edc61d4](https://github.com/Hapfel1/er-save-manager/commit/edc61d4a81269c94521f098e1a639489147c94e5))



### 🔧 Bug Fixes

- Fixed appimage build to include the custom lavender theme correctly ([381481d](https://github.com/Hapfel1/er-save-manager/commit/381481d5a8fec155b1cf598ce7105008837c96b5))

- Added vpn checker in troubleshooting tab ([d034cf3](https://github.com/Hapfel1/er-save-manager/commit/d034cf301effa169588d5f464af812b7dd9b1f8e))

- Added error for if the program is being run while zipped ([e7cb442](https://github.com/Hapfel1/er-save-manager/commit/e7cb4423c3dce2483aee93713f38d35082d4bb07))

- Fix steamdeck resolution issue ([2e9af76](https://github.com/Hapfel1/er-save-manager/commit/2e9af76cf060c4f5ddb730f53cd5b0495b47888b))

- Fixed wrong cnv save detection ([a213f99](https://github.com/Hapfel1/er-save-manager/commit/a213f99693b3188011b8251866f887cf616b7178))

- Fixed error when copying characters because of invalid filename characters, added sanitization ([22b83bb](https://github.com/Hapfel1/er-save-manager/commit/22b83bb87a162397c474159e1a86e424d1b25e85))

- Made opening links work on Linux ([f716d51](https://github.com/Hapfel1/er-save-manager/commit/f716d515b8329d5339639988a8caf6a4e24751c6))

- Fixed transferring characters between Save Files to correctly update Profile Summary and fixed an offset tracking error ([01ca69c](https://github.com/Hapfel1/er-save-manager/commit/01ca69c408244ba13a4bee912291923b1ead03f1))



### 🎨 User Interface

- Made autobackup more clear and easier to use ([572e8a3](https://github.com/Hapfel1/er-save-manager/commit/572e8a304214f6fa358d3bc2ea383670bf7da942))

- Revamped UI to work better for small resolution displays ([c058bd5](https://github.com/Hapfel1/er-save-manager/commit/c058bd55e846eea9b02592cae0902e6fceb45182))



### 📖 Documentation

- Updated TODO ([085914d](https://github.com/Hapfel1/er-save-manager/commit/085914dc2cfca94b3a45ab7c45180280fee08634))



### Buld

- Edit todo ([b996d7b](https://github.com/Hapfel1/er-save-manager/commit/b996d7beb4462e7d1110aaa126effdb1eb7c8f5f))



---
## 📦 Release 0.9.0
**Released:** February 03, 2026


### ✨ New Features

- Added export to JSON preset selection ([d969f24](https://github.com/Hapfel1/er-save-manager/commit/d969f249b0112d137637167d9f0fd238889f7a97))



### 🔧 Bug Fixes

- Correct case sensitivity for theme path on Linux ([88123da](https://github.com/Hapfel1/er-save-manager/commit/88123dabb5667a249d61e6b1eb572dcbd2ae578b))

- Fixed event flags being written incorrectly ([3e21c0d](https://github.com/Hapfel1/er-save-manager/commit/3e21c0dec72c1143b50c22658551dc3ac4faee77))

- Fixed save file backup functionality ([c49509e](https://github.com/Hapfel1/er-save-manager/commit/c49509e44d0de1f4e1d980e6542d095be91e0450))

- Fixed Character operation issues ([021d891](https://github.com/Hapfel1/er-save-manager/commit/021d8915425ed27d32fe112fd9f0aa13a2124516))

- Fixed info message popups appearing behind main window ([9ca2923](https://github.com/Hapfel1/er-save-manager/commit/9ca2923e501aac35bfe42ecabafd13eeb9b35dbb))



---
## 📦 Release 0.8.0
**Released:** February 02, 2026


### ✨ New Features

- Added version checker to notify users of new update ([757c4b1](https://github.com/Hapfel1/er-save-manager/commit/757c4b1a2a1c458e3ad3bc96c17e5147d2e34d72))

- Add Troubleshooter for checking game und save file related issues ([f0f850b](https://github.com/Hapfel1/er-save-manager/commit/f0f850b6050e0ef33f5092fdbb7374bfa2d45064))



### 🔧 Bug Fixes

- Fixed SteamDeck not showing Preset Browser correctly bc of SSL errors ([ea6794b](https://github.com/Hapfel1/er-save-manager/commit/ea6794b0cffdf812d1942a4158d79cbf3718e82c))



---
## 📦 Release 0.7.4
**Released:** January 31, 2026


### 🔧 Bug Fixes

- Fixed JSON import error msg ([36c73c1](https://github.com/Hapfel1/er-save-manager/commit/36c73c11f1d47fe9937b57b6757e796d83d81d66))



### 🎨 User Interface

- Change default theme to dark ([6516a42](https://github.com/Hapfel1/er-save-manager/commit/6516a42182316f9065677645df424c9087ca2c4f))



---
## 📦 Release 0.7.3
**Released:** January 30, 2026


### ✨ New Features

- Add ng+ editor in character info tab ([77f71af](https://github.com/Hapfel1/er-save-manager/commit/77f71afaed0bb9236c7ac72f2254e5705df5f971))



### 🔧 Bug Fixes

- Changed image display in the preset browser to always display the original image's resolution ([041733d](https://github.com/Hapfel1/er-save-manager/commit/041733db7e32cb082891f47039ac59440424338b))



### 🎨 User Interface

- Make save fixer description more clear and add auto loading upon selecting a save file ([7124a5a](https://github.com/Hapfel1/er-save-manager/commit/7124a5a794a42e4dc08224f557c6a2e759470bb7))

- Made all message boxes custom and improved the messagebox module ([dfa8685](https://github.com/Hapfel1/er-save-manager/commit/dfa86856f40c532b21240581bafcd257826a4140))

- Centered all popups to be in the middle of the parent's window ([a672e29](https://github.com/Hapfel1/er-save-manager/commit/a672e29a9ed1d7f8d1edd15434f5f0518c04117b))



### 📖 Documentation

- Update TODO ([8d5eb68](https://github.com/Hapfel1/er-save-manager/commit/8d5eb68096da0b93ace48d3de33a761b0138d355))



---
## 📦 Release 0.7.2
**Released:** January 30, 2026


---
## 📦 Release 0.7.1
**Released:** January 28, 2026


### 🔧 Bug Fixes

- Fixed error message pop-up when no actual error happened ([a5e6337](https://github.com/Hapfel1/er-save-manager/commit/a5e6337f8d2389588f0e6d3279ed771e4fa61b71))



---
## 📦 Release 0.7.0
**Released:** January 28, 2026


### ✨ New Features

- Add DLC flag clearing with conditional UI and teleport integration ([337cd83](https://github.com/Hapfel1/er-save-manager/commit/337cd837452dbc03910cc5bc5a62603d0dbb5218))



### 🔧 Bug Fixes

- Made all tabs scrollable, fixed typo ([ed9db29](https://github.com/Hapfel1/er-save-manager/commit/ed9db29da936f20855f262842e9642efbfba5472))

- Format & lint ([6fe1019](https://github.com/Hapfel1/er-save-manager/commit/6fe101902efe82b62f20116bd55b7fad58d5fa6d))



### 🎨 User Interface

- Fixed color issue in bright mode with character editor tab ([699cc32](https://github.com/Hapfel1/er-save-manager/commit/699cc32f66b0de5ca7b63f36a7ce9bf7a07b2e61))



---
## 📦 Release 0.6.2
**Released:** January 27, 2026


### 🔧 Bug Fixes

- Fixed workflow version numbering ([9d6c841](https://github.com/Hapfel1/er-save-manager/commit/9d6c84159c6ac555b9541b1752ee66b13bb85671))



---
## 📦 Release 0.6.1
**Released:** January 27, 2026


### 🔧 Bug Fixes

- Fixed version  bumping to include manifest and version info file ([883e0ea](https://github.com/Hapfel1/er-save-manager/commit/883e0ea179a8f48b412ef2509b6673c3fea02a83))



---
## 📦 Release 0.6.0
**Released:** January 27, 2026


### ✨ New Features

- Apply dark theme to character editor and fix CTkMessageBox calls `[ui]` ([e4ae35e](https://github.com/Hapfel1/er-save-manager/commit/e4ae35e15a0f57019551931344abeca4174a18b7))

- Community preset system with metrics, voting, and reporting ([71b0f50](https://github.com/Hapfel1/er-save-manager/commit/71b0f5078acc9fffff24a4e142d56992b7da6699))

- Cross-platform save file detection and Linux steam path improvements ([42f58a3](https://github.com/Hapfel1/er-save-manager/commit/42f58a3746695300449e1d3aa1b5dd4456af72ac))



### 🔧 Bug Fixes

- Improve save file loading and compatdata warnings ([3ed7393](https://github.com/Hapfel1/er-save-manager/commit/3ed739361a4e1c53ef6e435faae6bba958a04457))

- Format & lint ([e7ee415](https://github.com/Hapfel1/er-save-manager/commit/e7ee415a6a85924090428e01ae0286ee880fcb39))

- Fixed issues when running the appimage on linux ([cce2cbb](https://github.com/Hapfel1/er-save-manager/commit/cce2cbbf43d787fb63aa214cbd3b0545c381f3d4))

- Fix: linux tab rendering fixes
build: added logging to find out issue with appearance browser ([f13188d](https://github.com/Hapfel1/er-save-manager/commit/f13188d749311973b56add619e66a845a964b83c))

- Format & lint ([76f6856](https://github.com/Hapfel1/er-save-manager/commit/76f68563d0a444c36842db32fff834b3d297057f))

- Fix: Fixed PIL/Tkinter ingegration for Linux
Fixed Resource loading
Fixed "grab failed" issues ([d882972](https://github.com/Hapfel1/er-save-manager/commit/d882972843695e79647cd3b3a02b502283ab6fa0))

- Fixed eventflag binary search tree text file loading on linux ([cee75f7](https://github.com/Hapfel1/er-save-manager/commit/cee75f7581ce92b212d141f560fed6138a2fa837))

- Fixed correct resources import ([e07509b](https://github.com/Hapfel1/er-save-manager/commit/e07509b14c038afa403ce3e545107212d5e55afb))



### 🎨 User Interface

- Enhance preset browser and application UI ([834ba8c](https://github.com/Hapfel1/er-save-manager/commit/834ba8c6f727de6bca6107ca36b51e550721aad2))



### 📖 Documentation

- Complete documentation rewrite with feature status and architecture ([8f6742b](https://github.com/Hapfel1/er-save-manager/commit/8f6742bf6569988d2ca73534a5ae5f31c34578bd))

- Fixed documentation ([abc108c](https://github.com/Hapfel1/er-save-manager/commit/abc108cab70895e26fcbca92a3cf78954af58248))



### ⚡ Performance Improvements

- Optimize preset browser loading and caching ([27042ad](https://github.com/Hapfel1/er-save-manager/commit/27042ad0725bc60e4d31e3652bd0a42a4ce25452))



### 🧹 Maintenance

- Fix gitignore to track source data and fix region_ids_map ([23068a3](https://github.com/Hapfel1/er-save-manager/commit/23068a38a5066ef010490d3ebefc4ed90cfea59a))



---
## 📦 Release 0.5.1
**Released:** January 24, 2026


### 🔧 Bug Fixes

- Fixed import/export ([5bfb043](https://github.com/Hapfel1/er-save-manager/commit/5bfb0432cd0fc0db2583ff75129dfcb4e80e6775))

- Format & lint ([6f02075](https://github.com/Hapfel1/er-save-manager/commit/6f02075d337ee5083ec3d9949e4f49ed0b8e3ded))



---
## 📦 Release 0.5.0
**Released:** January 24, 2026


### ✨ New Features

- Major UI improvements and bug fixes ([b8dccbe](https://github.com/Hapfel1/er-save-manager/commit/b8dccbee8cd639d3545895d8b4807d9e110577eb))

- Complete SteamID patcher with custom URL resolution `[steamid]` ([f785b38](https://github.com/Hapfel1/er-save-manager/commit/f785b38c5a75a94b8809bc6c1b0672d7dd388e82))

- Implement comprehensive event flags and gestures systems ([7a21259](https://github.com/Hapfel1/er-save-manager/commit/7a21259615616e44cc5c127ddd2bc73c28ad9b58))

- Implement boss respawn function (not finished) ([c53687b](https://github.com/Hapfel1/er-save-manager/commit/c53687bca7459d9b1820fe63edac67b6588f4afe))

- Implement complete community character preset browser system `[ui]` ([4970826](https://github.com/Hapfel1/er-save-manager/commit/4970826bb953655840252fbd77d841cd54d55840))



### 🔧 Bug Fixes

- Small removal ([dfe4053](https://github.com/Hapfel1/er-save-manager/commit/dfe4053f1f98a76afbd3ac9b853aa516adb57292))

- Fix: removed temporary testing buttons
docs: updated tooltips for boss respawner ([fe4a601](https://github.com/Hapfel1/er-save-manager/commit/fe4a601c8e552e7e71701c665e1ec0127f927e5d))

- Lint % format ([e02108d](https://github.com/Hapfel1/er-save-manager/commit/e02108deda47e59bb84aab4d2bf5c2bfeabb2ab4))

- Fix: small fixes for UI
fix: fix appearance browser + add workflow for submission ([e898db2](https://github.com/Hapfel1/er-save-manager/commit/e898db276234052c419330d7cfb50785c50ecd6f))



### 📖 Documentation

- Updated TODO.md ([9e3b06f](https://github.com/Hapfel1/er-save-manager/commit/9e3b06fe1797ecef9f70737f980f4e347d22bcee))

- Updated TODO ([0fd8602](https://github.com/Hapfel1/er-save-manager/commit/0fd86026d024c86670d289b2f44ec8283ad37bee))



---
## 📦 Release 0.4.1
**Released:** January 23, 2026


### 🔧 Bug Fixes

- License format in pyproject.toml to combat deprecation warning ([0b81a37](https://github.com/Hapfel1/er-save-manager/commit/0b81a377c63a7e92c1d16db3a7420a2c2a4f3878))

- Fix deprecation issue with license ([336a556](https://github.com/Hapfel1/er-save-manager/commit/336a556cb682d259590550f5d979a71ab1dfba45))



---
## 📦 Release 0.4.0
**Released:** January 18, 2026


### ✨ New Features

- Add modular UI components ([1aa8d2a](https://github.com/Hapfel1/er-save-manager/commit/1aa8d2aa33373ab343cadcf14ded79d1038df944))

- Add modular GUI coordinator ([a2143bb](https://github.com/Hapfel1/er-save-manager/commit/a2143bb1a14cf1cf2ca430e0e81558ea7c80008a))

- Add item database for user-friendly names ([fd9d173](https://github.com/Hapfel1/er-save-manager/commit/fd9d173c370ffe3383697837883eae5bb5315198))



### 🔧 Bug Fixes

- Fixed cli to integrate new ui modules ([458a9dd](https://github.com/Hapfel1/er-save-manager/commit/458a9dddab3f2db80f389193332c9523890a6161))

- Update parser for GUI compatibility ([dbe8b22](https://github.com/Hapfel1/er-save-manager/commit/dbe8b2264822b4caaf7023e7452f56df2e6701d9))

- Format and lint ([31fbadd](https://github.com/Hapfel1/er-save-manager/commit/31fbadd6a85e6f574ccb1ccebe17246ff3c6d098))



### 🧹 Maintenance

- Update TODO and backup original GUI ([bf7ed93](https://github.com/Hapfel1/er-save-manager/commit/bf7ed93ac4c8c705c8be10a454a187c9c4fd048c))



---
## 📦 Release 0.3.0
**Released:** January 17, 2026


### ✨ New Features

- Add character operations module with dynamic offset tracking ([2101ae7](https://github.com/Hapfel1/er-save-manager/commit/2101ae77f2625ba83a14ddb7b5471e682fef07f2))

- Implement dynamic offset tracking in save parser ([70561b3](https://github.com/Hapfel1/er-save-manager/commit/70561b373a1f42673bc4d58b360fcfb15926f914))



### 🎨 User Interface

- Redesign character management with operation dropdown ([e3141fc](https://github.com/Hapfel1/er-save-manager/commit/e3141fcbba1cb715dac4390cdf324d4a75cf4746))



### 📖 Documentation

- Updated TODO.md ([5dcee10](https://github.com/Hapfel1/er-save-manager/commit/5dcee100522b6452ca9633bf26cd7f934ed6b961))



---
## 📦 Release 0.2.1
**Released:** January 17, 2026


### 🔧 Bug Fixes

- Convert all relative imports to absolute ([08b1611](https://github.com/Hapfel1/er-save-manager/commit/08b1611fe5b32fa2af9639c64d236d4267fbc614))



### 📖 Documentation

- Add TODO file with feature implementation roadmap ([6da025a](https://github.com/Hapfel1/er-save-manager/commit/6da025a88146e33b0f70a55c1ce34dd7ff1ed9e7))



---
## 📦 Release 0.2.0
**Released:** January 17, 2026


### ✨ New Features

- Add GUI launcher and fix Windows executable ([613e1c5](https://github.com/Hapfel1/er-save-manager/commit/613e1c5826cf692ac45f6e1e510665f09cefcc98))



### 🔧 Bug Fixes

- Use absolute import for cx_Freeze compatibility ([fb6bea2](https://github.com/Hapfel1/er-save-manager/commit/fb6bea2e7932d47d28ff78f67fc1836fa16624a2))

- Convert all relative imports to absolute for cx_Freeze compatibility ([1c5e95b](https://github.com/Hapfel1/er-save-manager/commit/1c5e95b170d6f504d6ae4bf525cfbc9638a9b235))

- Test auto release trigger ([7491182](https://github.com/Hapfel1/er-save-manager/commit/749118280ad56bb592125f8b1663590b567f1d60))

- Release workflow safety check and changelog extraction ([d87cde1](https://github.com/Hapfel1/er-save-manager/commit/d87cde15bb806602ec30f4de66f24f2080d5f924))

- Correct PR URL in cliff.toml template ([01e3d9e](https://github.com/Hapfel1/er-save-manager/commit/01e3d9eb1221d3cf2f59ec55277a64b9c1e4f065))



### 🧹 Maintenance

- Re-trigger release for 0.1.1 ([eef04dc](https://github.com/Hapfel1/er-save-manager/commit/eef04dcaf250bc747b2a8fe3b264aef9be86c242))

- Update repo URLs to upstream (Hapfel1) ([4121855](https://github.com/Hapfel1/er-save-manager/commit/4121855709c1bc82d1684198c83ebfc8e579270e))



---
## 📦 Release 0.1.0
**Released:** January 17, 2026


### ✨ New Features

- Added release workflow ([23d78a0](https://github.com/Hapfel1/er-save-manager/commit/23d78a0f88c0f2ea69ed5f7cce2f530a6c070ab4))

- Added gui, implemented functions partially ([f464292](https://github.com/Hapfel1/er-save-manager/commit/f464292b162e50b742a3bebaa77b5909e3d9e8e4))

- Feat: add new gui features (templates for further
implementation) ([77f66e6](https://github.com/Hapfel1/er-save-manager/commit/77f66e6a1d4f1b447076077fcc1cfd06a608daab))

- Add automatic release workflow and build scripts ([45d2d35](https://github.com/Hapfel1/er-save-manager/commit/45d2d352e042ecb5c6cb918eff391c4e69141107))



### 🔧 Bug Fixes

- Edited readme correctly ([2ac2bbf](https://github.com/Hapfel1/er-save-manager/commit/2ac2bbfd4e9467b2e61b72b8b640a8b095ab6a3a))

- README ([af552da](https://github.com/Hapfel1/er-save-manager/commit/af552da648184d5824f0e9bd3a8ae36fdf5bfdab))

- Lint and format ([a248bda](https://github.com/Hapfel1/er-save-manager/commit/a248bdac119d579495ff486ad6edcbcd5d873a11))

- Fix import ([1f2d05c](https://github.com/Hapfel1/er-save-manager/commit/1f2d05cb689939aa6a1a2f11dbcf5bd848401040))

- Set executable permissions for shell scripts ([5d47267](https://github.com/Hapfel1/er-save-manager/commit/5d47267d0179b74d6b937e093b47d7fcfaf76256))

- Fix ci.yml ([e94a478](https://github.com/Hapfel1/er-save-manager/commit/e94a478dbaf41dce38d8c39ffa313b7d3539d11b))



### 🧹 Maintenance

- Repo URLs in cliff.toml for upstream ([90bcc63](https://github.com/Hapfel1/er-save-manager/commit/90bcc63dff7db7eeb94e54394131d4fbaf1a01e4))



---
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

