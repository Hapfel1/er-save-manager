# 📜 ER Save Manager - Release History

> A comprehensive changelog for the Elden Ring Save Manager application.
> All notable changes to this project are documented here.

## 📦 Release 1.11.0
**Released:** September 23, 2026


### ✨ New Features

- Added Weapon-Batch-Upgrading to the Visual Inventory Editor: ([a3d30c5](https://github.com/Hapfel1/er-save-manager/commit/a3d30c53982fd6a76b692f457e50a8d89f60c031))

- Feat: added Convergence Mod sites of grace to EVENT_FLAGS and
FLAGS_BY_CATEGORY ([1cb7879](https://github.com/Hapfel1/er-save-manager/commit/1cb7879edcc96923bffc9d28fa258a69ee93b175))

- Add is_convergence helper ([d43d49b](https://github.com/Hapfel1/er-save-manager/commit/d43d49b1961e6bd0d419863c8fefba08ee05debd))

- Add Max button to batch weapon upgrade dialog ([baed03d](https://github.com/Hapfel1/er-save-manager/commit/baed03d1099f95562a4181d03e2eae089509be94))

- Add Sites of Grace dialog to the event flags tab `[er]` ([1dc2b67](https://github.com/Hapfel1/er-save-manager/commit/1dc2b67ff3e45258bf83bb8fce0d16a142bbe67b))

- Add show item IDs and custom ID item adder dev options `[er]` ([17a1321](https://github.com/Hapfel1/er-save-manager/commit/17a13216b8a757916563ddee920e5299af989811))



### 🔧 Bug Fixes

- Fix: get_flag_name now works like before the addition of EventFlagInfo
again ([ca07cbd](https://github.com/Hapfel1/er-save-manager/commit/ca07cbdc34115a366a458bc053796ac015a653ac))

- Remove duplicate id from wrong category ([bb3e4ec](https://github.com/Hapfel1/er-save-manager/commit/bb3e4ec94f49599b8b3491e9514161eadeac8895))

- Hide convergence-only subcategories and flags on non-convergence saves ([bdebe35](https://github.com/Hapfel1/er-save-manager/commit/bdebe3518dd203ad7f2067fe8c25e84caa5de5c9))

- Correct Forbidden Lands spelling in grace category ([ddc7af3](https://github.com/Hapfel1/er-save-manager/commit/ddc7af3cc01907a161186831618d22e6ad52eb72))

- Refresh subcategory dropdown filter when a save loads ([1c97a9d](https://github.com/Hapfel1/er-save-manager/commit/1c97a9dcdaa3747d839ca5fffcbf28eab57f3824))

- Clipped add button, seamless items, garbled slot names `[ds2]` ([2a3ca45](https://github.com/Hapfel1/er-save-manager/commit/2a3ca45725e5e75f1b599fe7adf8e7f9de3758d2))

- Stale flag render and stale filters in event flags tab ([4117065](https://github.com/Hapfel1/er-save-manager/commit/41170652936d9089e70b6f5fef3b0b03888a19a9))

- Correct item IDs and stop writing bogus unk_1 on new items `[ds2]` ([e70f38e](https://github.com/Hapfel1/er-save-manager/commit/e70f38e6f10e5e3e29b55c8b6537f4084c79e5ed))



### 🎨 User Interface

- Hide Convergence Mod exclusive flags from non Convergence Mod saves ([d67cb2d](https://github.com/Hapfel1/er-save-manager/commit/d67cb2da805db0798c73758a8c2140e9ec0b7d9a))



### 📦 Dependencies

- Bump the github-actions group with 2 updates `[deps]` ([c618e33](https://github.com/Hapfel1/er-save-manager/commit/c618e33a2bfc484086aee8b5675e748001e3247f))



---
## 📦 Release 1.10.3
**Released:** September 15, 2026


### 🔧 Bug Fixes

- Combo dropdown popup misplaced at (0,0) on Windows ([0193f15](https://github.com/Hapfel1/er-save-manager/commit/0193f15cc8363f9be506deb44d66fdd7bceae344))

- Add separate fix for Tarnished pack entry flag `[dlc]` ([0a17bb9](https://github.com/Hapfel1/er-save-manager/commit/0a17bb9a0973422313df2c73fa79db5d016a18fe))

- Resolve Convergence class list gaps `[classes]` ([ef59ce8](https://github.com/Hapfel1/er-save-manager/commit/ef59ce8f9e16ac0ad9d4ef2df071c8322e4908ff))

- Remove unneeded comparison and update outdated comment ([f6a1304](https://github.com/Hapfel1/er-save-manager/commit/f6a1304b09c1fb95a0adc3cce99a03f24241d044))



### 🎨 User Interface

- Replace category dropdown with scrollable popup ([d4630e9](https://github.com/Hapfel1/er-save-manager/commit/d4630e9b840618469966a9faef4a2a1da522e9d3))

- Replace CTkComboBox native dropdown with scrollable popup ([72b0768](https://github.com/Hapfel1/er-save-manager/commit/72b07687f934a48a6c1010a6e3aec9fc8e43e92e))



### 📖 Documentation

- Docs:add missing technical doc sections between BloodStain and Event
Flags ([a59a64f](https://github.com/Hapfel1/er-save-manager/commit/a59a64f5ca3bb8ddd71cd0e09562806fe80ef2d1))

- Docs:add missing technical doc sections between Event Flags and
PlayerCoordinates ([2290b43](https://github.com/Hapfel1/er-save-manager/commit/2290b43356522aaae88fd0b8b01c277baa0a8887))

- Docs(technical): correct wrong types for MenuSaveLoad, wrong offset for
FieldArea etc. and correct byte count for `event_flags_terminator` after
Event Flags ([620897b](https://github.com/Hapfel1/er-save-manager/commit/620897bf85ba1f196cea2379aeef0134da2e9373))

- Fix offsets for MenuSaveLoad and trim newlines `[technical]` ([7335f62](https://github.com/Hapfel1/er-save-manager/commit/7335f6246211f8e7ad69341706b481bcab8c0887))

- Fix offsets for all new sections, where applicable `[technical]` ([21ef932](https://github.com/Hapfel1/er-save-manager/commit/21ef9327afd1777e887c47ff0ab64c47f55aa067))



---
## 📦 Release 1.10.2
**Released:** September 11, 2026


### 🔧 Bug Fixes

- Match .cnv anywhere in filename, not just as suffix `[convergence]` ([d9c627d](https://github.com/Hapfel1/er-save-manager/commit/d9c627db648dbe9c4411a717c365a43359edd51c))

- Batch remove items by category in visual inventory `[inventory]` ([5e78ca6](https://github.com/Hapfel1/er-save-manager/commit/5e78ca6eca8a908a80b9646cda332b7259aae7ba))

- Added missing icons ([8481dd3](https://github.com/Hapfel1/er-save-manager/commit/8481dd3a6d3d6aee0d3a5ee0743a8a719368567f))



### 🎨 User Interface

- Add save/game version reference table `[version-mismatch]` ([8dbca69](https://github.com/Hapfel1/er-save-manager/commit/8dbca69a8c77e4c58e5cbec9bf725d2e42434a1d))



### 📖 Documentation

- Update Mistakes in Save-File-Structure Docs, added GaItem Description ([f22c53f](https://github.com/Hapfel1/er-save-manager/commit/f22c53fdf1b55838922adbfca13d81b12cbb566c))



### 📦 Dependencies

- Bump taiki-e/install-action in the github-actions group `[deps]` ([0d704e1](https://github.com/Hapfel1/er-save-manager/commit/0d704e13f878fbcff6a2b838dfa1a3e846301bef))



### Ds2

- Hide never-created slots from save inspector list ([cf14269](https://github.com/Hapfel1/er-save-manager/commit/cf14269ea07c132229cccb19c550631c9e98b3b3))



---
## 📦 Release 1.10.1
**Released:** September 02, 2026


### 🔧 Bug Fixes

- Add save/game version mismatch fix `[ui]` ([d3323fa](https://github.com/Hapfel1/er-save-manager/commit/d3323fa4eb2c16f7d6366f59fa431a74bfbc4802))



### 📦 Dependencies

- Bump urllib3 from 2.6.3 to 2.7.0 `[deps]` ([6107be0](https://github.com/Hapfel1/er-save-manager/commit/6107be003ebb1eaf59e8b640b4244f939fdf9f16))



---
## 📦 Release 1.10.0
**Released:** September 01, 2026


### ✨ New Features

- Add Tarnished Pack DLC items and DLC-gated content `[tarnished-pack]` ([6b7d265](https://github.com/Hapfel1/er-save-manager/commit/6b7d2658e9cd210431df1a2b85adbfb3791713f4))



### 🔧 Bug Fixes

- Added Tarnished Pack Starting Classes ([4d60fde](https://github.com/Hapfel1/er-save-manager/commit/4d60fdeeb95aef0f0113511bf4a32d6e1c2f7e7c))

- Prevent EAC warning from silently cancelling save load `[gui]` ([d3a50ea](https://github.com/Hapfel1/er-save-manager/commit/d3a50ead9f85353425d8f0f8cea7a5330d18c254))



### 📦 Dependencies

- Bump taiki-e/install-action in the github-actions group `[deps]` ([c915105](https://github.com/Hapfel1/er-save-manager/commit/c915105839ef22e55b3dec85fcd9ea92246a6ec5))

- Bump taiki-e/install-action in the github-actions group `[deps]` ([86f89a6](https://github.com/Hapfel1/er-save-manager/commit/86f89a671cf88f26e5c10825cdf932cf3794b05b))



---
## 📦 Release 1.9.1
**Released:** August 17, 2026


### 🔧 Bug Fixes

- Block save writes while the game is running `[ui]` ([0e93040](https://github.com/Hapfel1/er-save-manager/commit/0e9304046650c54107dd59cbeedd947cabe9cf9e))

- Allow visual inventory and icon browser open together `[inventory]` ([68e95d4](https://github.com/Hapfel1/er-save-manager/commit/68e95d4fcefcebd33a18980e6311e35b753db201))



### 🎨 User Interface

- Added option to lock/favorite backups which will never get purged/deleted `[backups]` ([a78e5c3](https://github.com/Hapfel1/er-save-manager/commit/a78e5c3a11fc795f7b34f3d2993225c8974fed3d))

- Added label/reason input field when creating manual backup, falls back to "manual" when left empty `[backup]` ([190cff4](https://github.com/Hapfel1/er-save-manager/commit/190cff486e23d619623bc3864f530c914c252b1c))

- Add sort control to the inventory editor list `[inventory]` ([70d76c3](https://github.com/Hapfel1/er-save-manager/commit/70d76c33c0a206f9e67dd76109b8ba863bd4c31e))



### 📦 Dependencies

- Bump the github-actions group with 2 updates `[deps]` ([3f845dd](https://github.com/Hapfel1/er-save-manager/commit/3f845dd7524cb821f8f04b9fa6d7bc3709e4b216))

- Bump pyjwt from 2.10.1 to 2.13.0 `[deps]` ([3bbcc7a](https://github.com/Hapfel1/er-save-manager/commit/3bbcc7adf2b9816631d8a474b4785aa0e05a3a70))



---
## 📦 Release 1.9.0
**Released:** August 11, 2026


### ✨ New Features

- Add interval-based auto-backup while game is running `[settings]` ([41685ed](https://github.com/Hapfel1/er-save-manager/commit/41685ed25f99eadf2df5ed2d3f3ce25810f93ebf))

- CodeQL advanced workflow (actions + python) ([43903a5](https://github.com/Hapfel1/er-save-manager/commit/43903a50bd8eb92ec07f441edbb319d6240c0ef5))



### 🔧 Bug Fixes

- Use correct empty-slot sentinel when writing gesture array `[gestures]` ([0ef4a2b](https://github.com/Hapfel1/er-save-manager/commit/0ef4a2bd1d4d583bc80a854924e78ddf6f191c5d))

- Added missed item, Lantern `[item-db]` ([03195e2](https://github.com/Hapfel1/er-save-manager/commit/03195e282e6b8fc8b3e3e31d0f379006ce593c5c))

- Add missed items for Convergence `[item_db]` ([89a74de](https://github.com/Hapfel1/er-save-manager/commit/89a74de5d9ee30c54e1c8341d6360334688368f0))

- Scope gaitem lookup to target inventory location `[inventory]` ([06fcf16](https://github.com/Hapfel1/er-save-manager/commit/06fcf1608d6370a66169215245edfec6c74a484e))

- Exclude orphaned gaitem_map entries from weapon/armor picker `[equipment-editor]` ([f851bae](https://github.com/Hapfel1/er-save-manager/commit/f851baeed1cccbb1ed1c10129e91bef48f012fa3))



### 📦 Dependencies

- Bump the github-actions group with 2 updates `[deps]` ([337dbfa](https://github.com/Hapfel1/er-save-manager/commit/337dbfa8ac1a9a31797f834bcb284986ee6dd07c))

- Bump taiki-e/install-action in the github-actions group `[deps]` ([5d52ae4](https://github.com/Hapfel1/er-save-manager/commit/5d52ae498310dd51c2256a754e1247a8d2becc4f))

- Bump pillow from 12.1.0 to 12.3.0 `[deps]` ([763c374](https://github.com/Hapfel1/er-save-manager/commit/763c3745e7773d09545a8f500c53ea6e3da4357d))

- Bump cryptography from 46.0.3 to 50.0.0 `[deps]` ([6f4373d](https://github.com/Hapfel1/er-save-manager/commit/6f4373d8f474af0da7cd077045390ca98aa40392))



---
## 📦 Release 1.8.0
**Released:** July 30, 2026


### ✨ New Features

- Fix for the "Missing Romina" bug ([3727d86](https://github.com/Hapfel1/er-save-manager/commit/3727d86718eaa0a1c76af9a97c6e078f93670b29))

- Ruins of Unte golem fix for Seamless Co-op ([0c6e0d1](https://github.com/Hapfel1/er-save-manager/commit/0c6e0d1e9d314bd1b80d2682dedbc613b5307087))

- Erdtree state detection ([793a2dc](https://github.com/Hapfel1/er-save-manager/commit/793a2dc0a1b4d2d16058aa40b45d629edf42a3d9))

- Add character management for DSR, DS3, and Nightreign `[character-ops]` ([16a7262](https://github.com/Hapfel1/er-save-manager/commit/16a7262dd189dcfbb692875c108bae29bfe6841c))

- Add Support for DS2 Save File Editing ([3590874](https://github.com/Hapfel1/er-save-manager/commit/3590874778484e9ed93b9e7dea7ddee29d3ae699))

- Back up before every write, sortable inventory columns, update steamid docs `[ds2]` ([7e04d2f](https://github.com/Hapfel1/er-save-manager/commit/7e04d2f568379e4cebd7c9bc622b683cca669f76))



### 🔧 Bug Fixes

- Fixed Typo and added flag 3001 which triggers NG on teleport to Roundtable Hold `[event_flags]` ([a38b256](https://github.com/Hapfel1/er-save-manager/commit/a38b2560e6beb981c08647d2ee4a14f3c19857ea))

- Sync qty/upgrade/location vars before batch add `[icon-browser]` ([13e4ddc](https://github.com/Hapfel1/er-save-manager/commit/13e4ddc41ae732a10b79924e7014923344ce9ed0))

- Use atomic writes in DS3, DSR, NR parsers and steamid patchers `[games]` ([c010f83](https://github.com/Hapfel1/er-save-manager/commit/c010f83ef2ceaf44825dfe68b7c869294563d745))

- Kill correct process when force-terminating non-ER games `[platform]` ([3f32cd8](https://github.com/Hapfel1/er-save-manager/commit/3f32cd852ac8211571ed62da003ac3799db4c147))

- Fixed Poisoned Hand being documented as smithing stone weapon, added unique armor set version to Convergence Armor `[item_db]` ([8306a20](https://github.com/Hapfel1/er-save-manager/commit/8306a20fa77044e9c6a7096ae70c959cb7e7553a))

- Commit max backups on enter/focus-out instead of every keystroke `[settings]` ([7f826b7](https://github.com/Hapfel1/er-save-manager/commit/7f826b76ff69e2f550634817a4dda3d9a9b70aec))

- Use native file dialogs for export/import/transfer `[character-ops]` ([0ab47a5](https://github.com/Hapfel1/er-save-manager/commit/0ab47a5684f1690f0c531077c117a36274f2d049))

- Add autofind + manual browse to transfer target picker `[character-ops]` ([2ea9233](https://github.com/Hapfel1/er-save-manager/commit/2ea9233da2550697bde9849c1cd615f79979a44d))

- Add auto-backup toast instead of popup message and add setting to disable it `[backup]` ([98941fd](https://github.com/Hapfel1/er-save-manager/commit/98941fd0c972d6186a20adee30c517b7a0b11888))

- Set all affinity unlock flags for whetblades `[inventory]` ([f67e889](https://github.com/Hapfel1/er-save-manager/commit/f67e889417fcc6c79640e7de1fe14c64088339b4))

- Warn before lowering max backups prunes existing backups `[settings]` ([de8d835](https://github.com/Hapfel1/er-save-manager/commit/de8d835677518090b186bf3e7dfead09ed6ba216))

- More UI fixes `[ds2]` ([4426585](https://github.com/Hapfel1/er-save-manager/commit/44265855c229a0de0d82bb20b30b60fbbdf00e2b))



### 🎨 User Interface

- Add note about  stale load-screen summary after copy/transfer `[character-ops]` ([c00382c](https://github.com/Hapfel1/er-save-manager/commit/c00382c1ecd7d98c78b0f1c1f0e5c4937c3e8713))



### 📖 Documentation

- Replace MIT with source-available license `[license]` ([5ae4eb5](https://github.com/Hapfel1/er-save-manager/commit/5ae4eb598c002fbc2f8d28fa95fc52000c816f16))

- Update license link in readme ([830214d](https://github.com/Hapfel1/er-save-manager/commit/830214dff784b2c9a9ecd5ff8d9d264260ac80a3))



### ♻️ Code Refactoring

- Resolve convergence items via item_database instead of missing hex files `[data]` ([d650262](https://github.com/Hapfel1/er-save-manager/commit/d650262f4ba9fd1105f979215715c81acb01d1db))



### 📦 Dependencies

- Bump the github-actions group with 3 updates `[deps]` ([fd3fe9e](https://github.com/Hapfel1/er-save-manager/commit/fd3fe9eeb1e2107739c5a1254952dcbe8977d6b0))



---
## 📦 Release 1.7.1
**Released:** July 22, 2026


### 🔧 Bug Fixes

- Fixed Browse Button not working on Linux with new native file explorer implementation ([59270c0](https://github.com/Hapfel1/er-save-manager/commit/59270c0158e4df34a802aba9f4de715f3491adce))

- Fixed missing Icons and duplicate Item Names ([aa0d664](https://github.com/Hapfel1/er-save-manager/commit/aa0d664159c048ad4f3daec4e5e838a916c9eed0))

- Add Native File PIcker for Lnux to "Save Icon" button in Visual Item Picker ([b0d78e8](https://github.com/Hapfel1/er-save-manager/commit/b0d78e8e5bfa1d9d3b5a3ec9de2be8c7c201ab69))



### 🎨 User Interface

- Fixed Padding for Icons ([34614b2](https://github.com/Hapfel1/er-save-manager/commit/34614b2fc8c26e1765b58059be20d773db71bf58))



---
## 📦 Release 1.7.0
**Released:** July 21, 2026


### ✨ New Features

- Add kill functionality mirroring respawn `[boss]` ([8bd48ff](https://github.com/Hapfel1/er-save-manager/commit/8bd48ff118fe9ef34ea62fbde415c6bba8d2df78))

- Add structural integrity scan module `[fixes]` ([9543a7a](https://github.com/Hapfel1/er-save-manager/commit/9543a7a70565f25d920e915fe183e2ef55d0e6f6))

- Add share-code import/export for appearance presets and inventory loadouts `[sharing]` ([2c4d259](https://github.com/Hapfel1/er-save-manager/commit/2c4d259abca4cf1da5131ef6ee106c0ac982dc65))

- Complete equipment editor - persistence fix, loadouts, visual picker `[equipment]` ([1303cdc](https://github.com/Hapfel1/er-save-manager/commit/1303cdc49de00c9d8df17cca3353e027c37d0586))



### 🔧 Bug Fixes

- Add missing CHECKSUM_SIZE class constant `[character_ops]` ([bffbe8b](https://github.com/Hapfel1/er-save-manager/commit/bffbe8beb150d7b9e5de154ca4a0ca43f3012eeb))

- Add Blessed Blue Dew Talisman Convergence variant to Convergence Talismans which reuses the Cerulean Seed Talisman's ID still with its old name in Params ([8cbd2d9](https://github.com/Hapfel1/er-save-manager/commit/8cbd2d9f3148e7a5a90f5a73637f9624b2d8a86f))

- Remove empty scrollable_frame widget and fix test exit code masking ([09b667d](https://github.com/Hapfel1/er-save-manager/commit/09b667d37009bd8b0330763a8ac7a61240a9890d))

- Include OpenSSL DLLs in root to prevent PATH conflicts under zip_include_packages `[build]` ([d9c08e7](https://github.com/Hapfel1/er-save-manager/commit/d9c08e77668380f85d669d0dd4e7418ff2f52eb2))

- Atomic save writes, unique backup names, preserve rebuild_slot tail data ([51f938d](https://github.com/Hapfel1/er-save-manager/commit/51f938deee42cdd05e97738c1f9e237c95e8da07))

- Use fixed 600 cap for ammo storage quantity `[inventory]` ([ec655b3](https://github.com/Hapfel1/er-save-manager/commit/ec655b3fb61dc74b80dbfc1ce3cf16cdd25e7b60))

- Added more Item event flag linking ([f72491b](https://github.com/Hapfel1/er-save-manager/commit/f72491b8cf9b7fbcbf4ef2bbaa174e3aa46afa4b))

- Fixcharacter-info): remove non-functional fields from info editor

Remove extra talisman slots, spirit summon level, max crimson flask, and max cerulean flask fields from the character info editor UI, load, and apply logic. These fields had no in-game effect when edited directly. ([cf5bc66](https://github.com/Hapfel1/er-save-manager/commit/cf5bc66cad117b3bb6320dcd2baf6997b61f52f0))

- Fixed earlier byte discarding fix getting reverted ([8e443b1](https://github.com/Hapfel1/er-save-manager/commit/8e443b1a78b6375878b1d334ba14e36db2e17966))

- Use fixed offset for NPC/event flag anchor instead of pattern search `[DSR]` ([0793494](https://github.com/Hapfel1/er-save-manager/commit/07934947ec69ad2ef20fb3b97ebbdc7731556690))



### 🎨 User Interface

- Show curse slot widgets for deep relics in editor `[NR]` ([3117279](https://github.com/Hapfel1/er-save-manager/commit/31172792002160479216a63a54535e4d14d8a962))

- Use native Linux file picker for all manual file browse dialogs ([3c3fc66](https://github.com/Hapfel1/er-save-manager/commit/3c3fc668a1f5356623dc5ade3a3c5a15ebb8505a))



### 📖 Documentation

- Fix fixer, character editor, event flags, world state, settings docs; add other-games guides ([081b472](https://github.com/Hapfel1/er-save-manager/commit/081b47205cc5757cb209ae7b580e301d617b8d24))



### 📦 Dependencies

- Bump the github-actions group with 2 updates `[deps]` ([a2d1bf4](https://github.com/Hapfel1/er-save-manager/commit/a2d1bf41ff429daa6b74380228f7005b47fcc981))

- Bump the github-actions group with 3 updates `[deps]` ([cdfa8bb](https://github.com/Hapfel1/er-save-manager/commit/cdfa8bba49c2d690d50c3d901ae796ddc6b27576))



---
## 📦 Release 1.6.2
**Released:** July 08, 2026


### 🔧 Bug Fixes

- Add missed Convergence Armor ([7451875](https://github.com/Hapfel1/er-save-manager/commit/7451875870c3330eea509a158fdecced7ac8f85a))

- Fallback to storage on held-full during add/batch/loadout `[inventory]` ([c13299c](https://github.com/Hapfel1/er-save-manager/commit/c13299c652dbc8768cdfd17099a8722315720006))



### 📦 Dependencies

- Bump the github-actions group with 2 updates `[deps]` ([3f3e1f6](https://github.com/Hapfel1/er-save-manager/commit/3f3e1f6b16e706fa4508a7bcb5e6a82d15f6d378))



---
## 📦 Release 1.6.1
**Released:** July 03, 2026


### 🔧 Bug Fixes

- Exclude compiled extension packages from Windows zip `[build]` ([aa1fea9](https://github.com/Hapfel1/er-save-manager/commit/aa1fea913c0b92f8dd27a6c467ada0ae399e5614))



---
## 📦 Release 1.6.0
**Released:** July 03, 2026


### ✨ New Features

- Add Elden Bling Auto Sliders JSON import ([7812ba0](https://github.com/Hapfel1/er-save-manager/commit/7812ba0ab8f6ef455e7554142191b01f7aeb79ef))



### 🔧 Bug Fixes

- Fall back to actual list when removing/setting quantity `[inventory]` ([228c389](https://github.com/Hapfel1/er-save-manager/commit/228c389443c9580f5a6fcd93660c689e936f5253))

- Shift all downstream slot offsets on gaitem insert/remove ([7eb3b4d](https://github.com/Hapfel1/er-save-manager/commit/7eb3b4d7fb0d2958177466b22276d57198d4f185))



### Data

- Add missing convergence items, fix item names, update icons ([1516d4f](https://github.com/Hapfel1/er-save-manager/commit/1516d4f1fb23109d568897437983fd90b02e9c16))



---
## 📦 Release 1.5.2
**Released:** June 29, 2026


### 🔧 Bug Fixes

- Correct consumable stack location and convergence upgrade caps (#193) ([7504329](https://github.com/Hapfel1/er-save-manager/commit/75043296d8e82fe28b49024c36ff325f35d8539b))

- Correct inventory counter updates for key items in add/remove ([1a483e9](https://github.com/Hapfel1/er-save-manager/commit/1a483e953bcea59eec23eaccede503fc0f707527))

- Trigger auto-backup on every game launch, not once per session `[backup]` ([36741ff](https://github.com/Hapfel1/er-save-manager/commit/36741ff435c747854329ac28fd3752090feb3eef))

- Rename invasion regions to unlocked regions ([c0cd80d](https://github.com/Hapfel1/er-save-manager/commit/c0cd80d9fcc585f02078e5bf875c838f1c086d9c))

- Detect and repair corrupted inventory item counters in character details ([f9020be](https://github.com/Hapfel1/er-save-manager/commit/f9020be0bb3738874e222d76f55d0d881ce94ff7))

- Add Event Flag mapping for maps and ashes of war ([9bde103](https://github.com/Hapfel1/er-save-manager/commit/9bde103548005a28fe2756f747faa5c53a730df1))



### 🎨 User Interface

- Add Video Guide button for Ghost's video guide ([d25fa56](https://github.com/Hapfel1/er-save-manager/commit/d25fa560229ed02b75d2b04846e3abececbb01c2))



### 📦 Dependencies

- Bump the github-actions group with 2 updates `[deps]` ([ff228e4](https://github.com/Hapfel1/er-save-manager/commit/ff228e4e5175a48e9e5c1055019ce48a82c4bba0))



### Data

- Migrate icon storage from zip to sqlite, fix nexus mods quarantine ([439f948](https://github.com/Hapfel1/er-save-manager/commit/439f9485eec4921eaf26ef0e49b954b69f836e36))



---
## 📦 Release 1.5.1
**Released:** June 23, 2026


### 🔧 Bug Fixes

- Update player_game_data_offset after gaitem shift and bump mm level on weapon spawn ([fc434b1](https://github.com/Hapfel1/er-save-manager/commit/fc434b1ff803312c8f58afc7c30feaafe8a6378b))

- Auto-adjust matchmaking level on weapon removal, remove manual set button ([a4e25a8](https://github.com/Hapfel1/er-save-manager/commit/a4e25a8936bf26c6284885af8773c29a5b7dd4d2))

- Added missed Convergence Item, Warding Remnant ([217e7a6](https://github.com/Hapfel1/er-save-manager/commit/217e7a619add1d766d78d0d4283e1ca55b4300b3))

- Add boss status dialog, fix bell bearing NG+ flags, fix search debounce (closes #189) ([2ed2d88](https://github.com/Hapfel1/er-save-manager/commit/2ed2d8830c181d51c2b2df5a3a52202f8129b280))

- Prevent integer overflow from corrupted acquisition indices `[inventory]` ([c6470f8](https://github.com/Hapfel1/er-save-manager/commit/c6470f8d323e34e084b5d2b147b99489fb650a9c))

- Adjust UI spacing and resolve loadout file path `[inventory]` ([6fe6676](https://github.com/Hapfel1/er-save-manager/commit/6fe6676894eabe43d1cb668b8fe7e650275849c3))



### 🎨 User Interface

- Made CSNetMan.bin replace button show permanently ([14700af](https://github.com/Hapfel1/er-save-manager/commit/14700affc1ef25f904b9ce13af8d0fa2aed3764b))

- Made Message about CsNetMan more clear ([09b9267](https://github.com/Hapfel1/er-save-manager/commit/09b92670ab4cc9f5479dd4d32371285c1e3fe954))

- Add Debug warped face button ([04bba00](https://github.com/Hapfel1/er-save-manager/commit/04bba002c301ce2cf5a2855fdc4b7541ab33464e))

- Add loadout manager, batch spawning, and smart stacking `[inventory]` ([77b09b6](https://github.com/Hapfel1/er-save-manager/commit/77b09b65dd5e9c118d2318f9519492363dbc4888))

- Replace warped face button with slider dialog for secondary face deformation ([bcb73dd](https://github.com/Hapfel1/er-save-manager/commit/bcb73dd2530aaa8ffd8142c0b1ecf3b5909108c3))



### ♻️ Code Refactoring

- Remove CSNetMan replace button toggle setting ([c6be1d3](https://github.com/Hapfel1/er-save-manager/commit/c6be1d34d70774a411829909774e1f7dc9baf979))



### 📦 Dependencies

- Bump the github-actions group with 3 updates `[deps]` ([249e547](https://github.com/Hapfel1/er-save-manager/commit/249e54759b33461be16013e184e3f71f31410fe9))



### 🧹 Maintenance

- Migrate nexusmods upload action to v1.0.0-beta.8 ([a51f7dc](https://github.com/Hapfel1/er-save-manager/commit/a51f7dc8fd3372978d3668e7e073f1aec33d805d))



---
## 📦 Release 1.5.0
**Released:** June 18, 2026


### ✨ New Features

- Add Nightreign save editor `[NR]` ([9606d27](https://github.com/Hapfel1/er-save-manager/commit/9606d27fe98bee7f1d502643c8f34d7efa9d829b))

- Add 3.0 update support `[convergence]` ([c0152c7](https://github.com/Hapfel1/er-save-manager/commit/c0152c7f03b2c84a503c06f6b69323cfbcc007df))



### 🔧 Bug Fixes

- Fix relics tab layout in fixed-height window `[NR]` ([38a778c](https://github.com/Hapfel1/er-save-manager/commit/38a778ce85639916bc0ac3ade9cc1db17fe79de7))

- Removed cut content cookbooks ([d68ad4a](https://github.com/Hapfel1/er-save-manager/commit/d68ad4abceb6d720ccacc5c2381ac04c6b4e102f))

- Cookbook/whetblade event flags and display fixes `[inventory]` ([5d3eed4](https://github.com/Hapfel1/er-save-manager/commit/5d3eed4e371594dfa54491dc06c05965d0eb7496))

- Expand _KEY_ITEM_BASE_IDS with all confirmed key item categories `[inventory]` ([1d23cec](https://github.com/Hapfel1/er-save-manager/commit/1d23cec7abdc0270e22ff10b5ebb5a4d3e719fb2))

- Remove cut content and fix item names across goods CSVs `[items]` ([2527929](https://github.com/Hapfel1/er-save-manager/commit/25279298f5e0589548e5ad7f24fff9180068a7e0))

- Add containers and upgrade items to _KEY_ITEM_BASE_IDS `[inventory]` ([8abb756](https://github.com/Hapfel1/er-save-manager/commit/8abb7568182972ca0890136260f7ef352e748f22))

- Add Dragon Heart and Lost Ashes of War to _KEY_ITEM_BASE_IDS `[inventory]` ([c226241](https://github.com/Hapfel1/er-save-manager/commit/c226241c94ff3b0e6e78759d1aeb85f80eac1c52))

- Remove two cut content items ([ade100e](https://github.com/Hapfel1/er-save-manager/commit/ade100e8cd05c5046f4ff58afa94994b1eebb2d4))



### 🎨 User Interface

- Ui: Fixed Icons being the same for modified variants of certain Items:
Lord of Blood's Favor
Unalloyed Gold Needle
Miniature Ranni
Academy Glintstone Key
Larval Tear ([53d9306](https://github.com/Hapfel1/er-save-manager/commit/53d9306fa7eae668e7f8dd9ab070f5be31aa512c))

- Replace pruning warning with pre-deletion CTk dialog `[backup]` ([780027e](https://github.com/Hapfel1/er-save-manager/commit/780027e24430b42bdef109d04d7c5e0ca2e2df72))



### 📦 Dependencies

- Bump taiki-e/install-action in the github-actions group `[deps]` ([f5f7167](https://github.com/Hapfel1/er-save-manager/commit/f5f716791de66b40387994b29f9260f2d61294c0))



---
## 📦 Release 1.4.1
**Released:** June 09, 2026


### 🔧 Bug Fixes

- Ashes Name Resolution, Allow Duplicate Talismans, Fix Melee filter exlcuding infused weapons in visual inventory ([4db254e](https://github.com/Hapfel1/er-save-manager/commit/4db254e63b285407e7edfa229d8eb19f875acdc5))

- Removed "No Presets" warning as this is not needed anymore and is possible now ([0e50b2f](https://github.com/Hapfel1/er-save-manager/commit/0e50b2fc8f90d761e1f4b7d064211c270bde9087))

- Fix incorrect starting class ID assignment #169 ([aaf2c67](https://github.com/Hapfel1/er-save-manager/commit/aaf2c67b330e044c5f879765cdd189162a17e56d))

- Enforce class stat minimums in stats editor, notify on archetype change ([23921e9](https://github.com/Hapfel1/er-save-manager/commit/23921e917cd8ed2a893ca04f246428acd9b9ef20))

- Correct wrong IDs for 8 ashes in Ashes.csv and DLCAshes.csv #170 ([2cd8152](https://github.com/Hapfel1/er-save-manager/commit/2cd815200fcaad6b0379957107794dc12683c42c))

- Correct body type encoding, NPC alive/dead offset handling `[DSR]` ([a3556b9](https://github.com/Hapfel1/er-save-manager/commit/a3556b95d9bcb17f67d6d843c4a4ed15fab7d210))

- Match gems in gaitem map by base_id via handle prefix ([83f1810](https://github.com/Hapfel1/er-save-manager/commit/83f1810cb7f2953f524ec8a9b989db56c2c52fb6))

- Hide PS button for non-ER games, fix item gib DS3 nav, restore SteamID tab position on PC save reloadfix: hide PS button for non-ER games, fix item gib DS3 nav, restore SteamID tab position on PC save reload ([cf2f811](https://github.com/Hapfel1/er-save-manager/commit/cf2f811dc6eb111d0078eb1df52234023c20d5f2))

- Mirror gaitem handle second byte from save; add held→storage fallback ([5c0e147](https://github.com/Hapfel1/er-save-manager/commit/5c0e1478e4ce7da873d96c2474f318bd4fbe6649))

- Redo Item DB by getting data from Params ([8ca9edf](https://github.com/Hapfel1/er-save-manager/commit/8ca9edfdba9f3aa55a4ad466922dbe7a66f12772))

- Match gem gaitem by base_id or full_item_id ([e4b1a97](https://github.com/Hapfel1/er-save-manager/commit/e4b1a97f15fdac97da5c55e953bca1da992ef745))

- Fix weapon spawn `[DS3]` ([be6beba](https://github.com/Hapfel1/er-save-manager/commit/be6bebabaa5153a1a215afcfe4e96b7dcfe97602))

- Accept more formats in the appearance tab JSON import ([63b82db](https://github.com/Hapfel1/er-save-manager/commit/63b82db5f5aaf2c30b33b8d844e3de1b1766e9b5))

- Potential PS fix for spawning weapons ([be98eb3](https://github.com/Hapfel1/er-save-manager/commit/be98eb337bf177fad64fe84ead15ad28fa0f3c24))

- Read second byte from first gaitem entry and reuse it for all spawned handle ([a3ff305](https://github.com/Hapfel1/er-save-manager/commit/a3ff3057ec493882f042e649565b934119b5387a))

- Default UI scale to 100% instead of Auto ([bc76ee9](https://github.com/Hapfel1/er-save-manager/commit/bc76ee9540c142c7e4b24cd7b47606dd0b8099d5))

- Lazy-load preset thumbnails in background threads ([778d164](https://github.com/Hapfel1/er-save-manager/commit/778d1645d49a5261308c8b1b57f1bfde000f4505))



### 🎨 User Interface

- Added Display Scale Setting ([07d394d](https://github.com/Hapfel1/er-save-manager/commit/07d394d5b6bd2a89e4dd1b9f7f716fc412b47da8))

- Add 104 NPC appearance presets to the preset browser ([9664509](https://github.com/Hapfel1/er-save-manager/commit/9664509bfacce1fe257793c2c871d1c35ec7e697))



### 📦 Dependencies

- Bump the github-actions group with 3 updates `[deps]` ([4aa7609](https://github.com/Hapfel1/er-save-manager/commit/4aa7609d0ea920b7ad2ce027d37323e643dd9395))



---
## 📦 Release 1.4.0
**Released:** June 04, 2026


### ✨ New Features

- Add DS3 save file editing `[DS3]` ([90b1830](https://github.com/Hapfel1/er-save-manager/commit/90b1830d235844369d4c020ca7990f78554aa582))

- Add Item Spawning `[DS3]` ([4495fea](https://github.com/Hapfel1/er-save-manager/commit/4495fea46ccdaa032852dd2c59969fb9e6f930c1))

- Added PlayStation Save File Reading and Editing `[ER]` ([5cc96a9](https://github.com/Hapfel1/er-save-manager/commit/5cc96a949c388081f935c1befb078740d035f034))

- Add DS3 save file editor module `[DS3]` ([1c18773](https://github.com/Hapfel1/er-save-manager/commit/1c18773290054fb3a41f3c33e906611961344c91))



### 🔧 Bug Fixes

- Added probing to find correct inventory size ([fb74414](https://github.com/Hapfel1/er-save-manager/commit/fb74414ae89c5157ab05a40ae5dd3aee38efd96e))

- Preserve global array header when writing to preset slot 0 ([4bfa53a](https://github.com/Hapfel1/er-save-manager/commit/4bfa53a6cbdb726ea95c0ecee3b79e664ae1ba70))

- Added mising Convergence Item, Putrid Key ([79d276d](https://github.com/Hapfel1/er-save-manager/commit/79d276d9ae6cac5d178168197005b2f9d1e260bc))

- Route key items to key_items[] in inventory ops ([89c6576](https://github.com/Hapfel1/er-save-manager/commit/89c65768e7d8785a62dc0b649c10db67c724047b))

- Skip checksum prefix on PS saves for all slot writes ([ace141d](https://github.com/Hapfel1/er-save-manager/commit/ace141d04c19b960f8b69681322cf2ef0e7da59c))

- Correct event flag base offset, add level recalc, flag lookup tab `[DSR]` ([0733060](https://github.com/Hapfel1/er-save-manager/commit/07330607a06803985a7ba6236e4bc6c42b6e8f1d))



### 🎨 User Interface

- Redid character transferring between files flow to make it more user friendly ([08a9649](https://github.com/Hapfel1/er-save-manager/commit/08a964973bbb70aae74a232edbf86e2854374d6d))

- Add info about quest steps that stay applied even after fully resetting quest progress ([4855469](https://github.com/Hapfel1/er-save-manager/commit/4855469724289a3c029a5ceb3f7bbe1299a3db63))

- Fix scroll bar bug in Icon Browser ([0ba6589](https://github.com/Hapfel1/er-save-manager/commit/0ba65890345260872f7cdec86d1da11e2f23a7cf))

- Rewrite info text to adjust for Switch and Playstation saves ([0eb0c01](https://github.com/Hapfel1/er-save-manager/commit/0eb0c013e770ca65ec2db50f5dfe8311fa851e64))



### 📦 Dependencies

- Bump the github-actions group with 2 updates `[deps]` ([3b3747f](https://github.com/Hapfel1/er-save-manager/commit/3b3747f529a391a56742fd3df45202c4076319dd))



---
## 📦 Release 1.3.2
**Released:** May 29, 2026


### 🔧 Bug Fixes

- Fixed some convergence weapons having affinity options when they should not have them ([9e77aaa](https://github.com/Hapfel1/er-save-manager/commit/9e77aaa2d874f64836206a69d1582dc60fb72b4c))

- Added missed SeamlessCoop Item (Crimson Blossom) `[DSR]` ([6f85f1b](https://github.com/Hapfel1/er-save-manager/commit/6f85f1b3c46bf2d83b5615508281a071f3c994fb))

- Added missing Attribute level validation ([cadf1a6](https://github.com/Hapfel1/er-save-manager/commit/cadf1a6911f3dfc88d2d873feb05e6dd4b7334fd))



### 🎨 User Interface

- Added SeamlessCoop Items for DSR ([bc3bc3b](https://github.com/Hapfel1/er-save-manager/commit/bc3bc3bc7a225d95388997963aa8ca3718740ee9))

- Added setting to disable "Save File modified externally" warning ([cabe487](https://github.com/Hapfel1/er-save-manager/commit/cabe487278d6f2c1b7cf35ed16598c1f3aa47c06))

- Fixed Search Indexing Bug in Icon Browser ([1a86722](https://github.com/Hapfel1/er-save-manager/commit/1a867220d65588ba93c97c8c20ae4bf4669e2975))

- Remove unnecessary popup when editing stats and also instantly change the level total in CSProfileSummary when total level changes ([43e6a3b](https://github.com/Hapfel1/er-save-manager/commit/43e6a3b29220c05cda77a9cefc64e4cd33674485))



---
## 📦 Release 1.3.1
**Released:** May 26, 2026


### 🔧 Bug Fixes

- Added missed Convergence Items (Maps and Perfumer quest items) ([fe6a843](https://github.com/Hapfel1/er-save-manager/commit/fe6a84355359b1fa538b0d3f1c10587b5395b435))

- Fixed issue with interpreting int level making it unable to apply NG+7 ([1002d35](https://github.com/Hapfel1/er-save-manager/commit/1002d35da7cc05e08e7e7b899c9903d5ed166f6c))

- Fixed build issue ([68ac838](https://github.com/Hapfel1/er-save-manager/commit/68ac8387acfdc0e7b4f09ccc71bd0d3db7d8cbe8))

- Write CSNetMan.bin at net_man_offset - 4 `[netman]` ([c2f73e7](https://github.com/Hapfel1/er-save-manager/commit/c2f73e765ab075633fe08533892d1382dd78cdaf))

- Fully implemented Affinity/Gem Validation for Convergence Saves ([4a90b21](https://github.com/Hapfel1/er-save-manager/commit/4a90b2151adaebdea05600d8525db73e94dcba66))



### 🎨 User Interface

- Add .cnv to the browse option filter ([c860719](https://github.com/Hapfel1/er-save-manager/commit/c8607194afaadff94b8ce33db5cbd273ffe94fc1))

- Fixed "Save File has been modified externally" popping up after modifying the save file with the manager ([7cd52f2](https://github.com/Hapfel1/er-save-manager/commit/7cd52f2083c4ac3371fd3094c1cdd102d5be36f7))



### 📦 Dependencies

- Bump taiki-e/install-action in the github-actions group `[deps]` ([7c6dafc](https://github.com/Hapfel1/er-save-manager/commit/7c6dafcea0ff5149ca1637d03fab77fd61bddf26))



---
## 📦 Release 1.3.0
**Released:** May 22, 2026


### ✨ New Features

- Add DSR Save Editing: Stats Editor, Inventory Editor, NPC&Boss Revival, World State ([91bc158](https://github.com/Hapfel1/er-save-manager/commit/91bc158629cc4d25d81c28bbabeccc7be5cd1434))

- Added Summoning Pool Button to the event flags tab to disable and enable summoning pools ([9367dc9](https://github.com/Hapfel1/er-save-manager/commit/9367dc916094e801d45b0de3d51df9035c88a3c9))



### 🔧 Bug Fixes

- Removed cut magic ([a3b0218](https://github.com/Hapfel1/er-save-manager/commit/a3b0218273cf92edaea3165caa61b806840ab4c3))

- Added early return for a guard that caused a crash ([2686335](https://github.com/Hapfel1/er-save-manager/commit/2686335ae4d420f095b2e014714b67752492b302))



### 🎨 User Interface

- Add new popup when a loaded save file gets modified externally ([f4291e9](https://github.com/Hapfel1/er-save-manager/commit/f4291e92d64edf8b9a254cf6b3e6ab372279e403))

- Improve DSR tabs `[DSR]` ([0738dbe](https://github.com/Hapfel1/er-save-manager/commit/0738dbecb5cb509cc89c1dc14f59a9df7a3c30cf))

- Add missing Convergence Armor ([668be41](https://github.com/Hapfel1/er-save-manager/commit/668be41fcc732f54cc883b9f5e515c560f49366e))



---
## 📦 Release 1.2.2
**Released:** May 19, 2026


### 📦 Dependencies

- Bump taiki-e/install-action in the github-actions group `[deps]` ([a5dfbd5](https://github.com/Hapfel1/er-save-manager/commit/a5dfbd58fb066fb6668f2694b8e7bbbc075d5516))



---
## 📦 Release 1.2.1
**Released:** May 14, 2026


### 🔧 Bug Fixes

- Inventory update operations and crashing issue ([9faf298](https://github.com/Hapfel1/er-save-manager/commit/9faf298484412d772981df6c0bd24af8974eb808))

- Fixed Convergence IDs that collided with base game IDs overwriting base game item names on non convergence saves ([077e6ba](https://github.com/Hapfel1/er-save-manager/commit/077e6baead17ae130760a4c8ec49ad08c88e8ad0))

- Fixed icon display issues, updated database ([b2e399a](https://github.com/Hapfel1/er-save-manager/commit/b2e399a4be072e26e1391ca7710b61e991c636e9))

- Fix nyasu import to correctly import talisman pouches and memory slots ([864c4a2](https://github.com/Hapfel1/er-save-manager/commit/864c4a22f6180cb321fb4d141397dd49aa867a5b))



### 🎨 User Interface

- Added view as icons for all items to make it  more user friendly ([89d17b6](https://github.com/Hapfel1/er-save-manager/commit/89d17b6857f41b4dca17c652314f4fb69f515467))

- Added Visual Inventory ([0df8d9b](https://github.com/Hapfel1/er-save-manager/commit/0df8d9b4bdbef98d645640d308f8f7dea39014ff))

- Added full visual Item Picker ([3950e72](https://github.com/Hapfel1/er-save-manager/commit/3950e72f6bccf55b57ec334be7518f2ad8339a6e))

- Increased Font Size and centered all new popups ([f92ea6b](https://github.com/Hapfel1/er-save-manager/commit/f92ea6b69d882328df02044c8d3e160da4cc0225))



---
## 📦 Release 1.2.0
**Released:** May 12, 2026


### ✨ New Features

- Added more modification to existing items in inventory (set affinity, aow, upgrade level) with the correct validation ([159a601](https://github.com/Hapfel1/er-save-manager/commit/159a6018f74989a1a01c4f8dea17a1a0ab2be5bc))



### 🔧 Bug Fixes

- Fixed unkown item ids showing up ([6698c2f](https://github.com/Hapfel1/er-save-manager/commit/6698c2f05bc5b244df41f4304c4a3bf5601e8beb))

- Fixed Weapon mm level calculation ([4556ba3](https://github.com/Hapfel1/er-save-manager/commit/4556ba3e32a0a82989f9f837ba5b7282d7d19e03))

- Correct EF tear false positive and remove unreliable anchor override `[deep_scan]` ([1b7c7e0](https://github.com/Hapfel1/er-save-manager/commit/1b7c7e0d9a592ef511e9e72f24a41cd5c014f38a))

- Fix update inventory ops with rebuild to fix crashing issue

Co-authored-by: Copilot <copilot@github.com> ([677bb93](https://github.com/Hapfel1/er-save-manager/commit/677bb930ccca2f75c44c19d8f2874f700dcd82d5))

- Improve Item Spawning to avoid crashing/corruption ([debf795](https://github.com/Hapfel1/er-save-manager/commit/debf7959cde268f132e0303178098e1de16a2b94))

- Fixed Item Import and slot rebuild to cause more corruption issues ([9ec6054](https://github.com/Hapfel1/er-save-manager/commit/9ec6054a8a73c6a2f82c5e99c246b204e28c2100))

- Add maxrepositorynum ([bfed293](https://github.com/Hapfel1/er-save-manager/commit/bfed293b477573096afa0f436f4ca77ca04a6235))



### 🎨 User Interface

- Add ItemGib button ([05c9c1f](https://github.com/Hapfel1/er-save-manager/commit/05c9c1f0cc1783d7a871390a5467603c2418919b))



### 📦 Dependencies

- Bump taiki-e/install-action in the github-actions group `[deps]` ([8a4c888](https://github.com/Hapfel1/er-save-manager/commit/8a4c888890363c0405b45c90c485251245acc06c))



---
## 📦 Release 1.1.0
**Released:** May 04, 2026


### ✨ New Features

- Structured item data with param validation `[inventory]` ([28b5b84](https://github.com/Hapfel1/er-save-manager/commit/28b5b84a8faa034d9de3872aba9ad3cd3c9d8d3d))



### 🔧 Bug Fixes

- Remove_item was ignoring the delta return value so it did not shift the offsets correctly ([7cccd3d](https://github.com/Hapfel1/er-save-manager/commit/7cccd3d76df24b8a924763ecb1961862dc48db44))

- Converted Database files to csv, added more params to validate each spawned item, split up add_item function ([a18ef1f](https://github.com/Hapfel1/er-save-manager/commit/a18ef1f8290461ff896efd620240faf5e60f7cbd))



### 📦 Dependencies

- Bump taiki-e/install-action in the github-actions group `[deps]` ([0d73cd8](https://github.com/Hapfel1/er-save-manager/commit/0d73cd8d90d4ed2eb8d708c374549d284afc2c06))



---
## 📦 Release 1.0.0
**Released:** May 03, 2026


### ✨ New Features

- Added Item Spawning ([2bf7b41](https://github.com/Hapfel1/er-save-manager/commit/2bf7b4165f56a02c55d73f398515a2ab87d6f3db))

- Added Equipment Editing ([c6aef6e](https://github.com/Hapfel1/er-save-manager/commit/c6aef6e27113ca6ee01332580ae059fa0db410c9))

- Added Item Spawning ([3569e06](https://github.com/Hapfel1/er-save-manager/commit/3569e067163db9287daad2740381cbf9b9379f00))

- Release v1.0.0 ([d54a0de](https://github.com/Hapfel1/er-save-manager/commit/d54a0de00aefca7388629e4877c8db655d1b37b6)) ⚠️ **BREAKING CHANGE**



### 🔧 Bug Fixes

- Fixed equipment editor not creating backups ([67abf43](https://github.com/Hapfel1/er-save-manager/commit/67abf43839062a0e6f56f8e67a549d4c787dd847))

- Fixed deep scan issues ([678a99a](https://github.com/Hapfel1/er-save-manager/commit/678a99ad33664e6f2246173cbe9c7936b9c2f803))



### 🎨 User Interface

- Rework vanilla save warning ([c73b2ca](https://github.com/Hapfel1/er-save-manager/commit/c73b2ca8776b604e66b9151b9235b773b38e6642))

- Remade Inventory Editor UI and added Affinities ([777eb0d](https://github.com/Hapfel1/er-save-manager/commit/777eb0d4a666a5fb8c8209f903f50f1a5ac4a89e))



### 📦 Dependencies

- Bump taiki-e/install-action in the github-actions group `[deps]` ([288d056](https://github.com/Hapfel1/er-save-manager/commit/288d056ec55d43455a8364f9d66da5bcfb75fbc8))



---
## 📦 Release 0.14.1
**Released:** April 22, 2026


### 🔧 Bug Fixes

- Add replacenetman option and button for trashed csnetmans without visible write torns ([23ff547](https://github.com/Hapfel1/er-save-manager/commit/23ff5474f5db3fab3133dcde17af8e862b8dbd3e))

- Fixed steamid not being synced correctly when importing from a .erc file ([4d3c9d9](https://github.com/Hapfel1/er-save-manager/commit/4d3c9d91bb0ab9f2dae405e6f0fa49ecbcd85ff2))



### 🎨 User Interface

- Add import flags button and add "All" selection for event flag categories with subcategories ([9c87496](https://github.com/Hapfel1/er-save-manager/commit/9c874962f3f64c05f831de3dfd2b337911a9372b))

- Added Playtime Editor ([555ed85](https://github.com/Hapfel1/er-save-manager/commit/555ed85fca02ea6924baa1be42fdb0173214cc8b))



### 📦 Dependencies

- Bump the github-actions group with 2 updates `[deps]` ([173e6f1](https://github.com/Hapfel1/er-save-manager/commit/173e6f1287b3165f094ac2eccfbe7874c316e42b))

- Bump the github-actions group with 2 updates `[deps]` ([1f9f899](https://github.com/Hapfel1/er-save-manager/commit/1f9f8998cc0b27a6bad36babf840c61294387517))



---
## 📦 Release 0.14.0
**Released:** April 10, 2026


### ✨ New Features

- Add weapon_matchmaking_level and a check for every weapon upgrade level to combat any tries to abuse modifying it ([e715c02](https://github.com/Hapfel1/er-save-manager/commit/e715c02793ab2d6757911f0510977eeff2563248))



### 🔧 Bug Fixes

- Fixed SteamID auto-detection on Linux ([debc036](https://github.com/Hapfel1/er-save-manager/commit/debc036c555521cf1f1116ce10187b8922ef8d23))

- Fixed Steam vanity link parsing ([150ed43](https://github.com/Hapfel1/er-save-manager/commit/150ed43545e3b570a17b588e95b5b46cb57f5f63))

- Fix Open folder button on certain Linux distros not working ([ca4edd0](https://github.com/Hapfel1/er-save-manager/commit/ca4edd01297a5e80d4b438740fd2f7ad83794529))

- Fixed the upgrade level detection ([33c9f5d](https://github.com/Hapfel1/er-save-manager/commit/33c9f5dfb55d49c0e2b7c0913a2e24d01a8c1c8f))

- Fixed process monitoring ([f9dfad4](https://github.com/Hapfel1/er-save-manager/commit/f9dfad4e5d7fd6130918170791b655ac53e31db9))

- Fixed process detection for is_game_running ([31eb4e9](https://github.com/Hapfel1/er-save-manager/commit/31eb4e9bb6c66936e0f38c624fb3312f0bdb9589))

- Fixed character name not being read correctly because of garbage data ([a5b40e1](https://github.com/Hapfel1/er-save-manager/commit/a5b40e15842515c940cf4023a838c0f1dfc52a96))

- Format and lint ([d4c374c](https://github.com/Hapfel1/er-save-manager/commit/d4c374c56ea08d1a1832cecf50f889fd5d392d9e))

- Fixed png issue with character browser and impoved loading in the browser ([3e74123](https://github.com/Hapfel1/er-save-manager/commit/3e741233895a947f15544551468d535a4cdedb37))

- Fixed cpu0 feature not applying correctly ([b6ad4a7](https://github.com/Hapfel1/er-save-manager/commit/b6ad4a7beac5779882b406f9430363c3daec5872))

- Lint ([62fab68](https://github.com/Hapfel1/er-save-manager/commit/62fab6810fb5c1bee51d972c7b438e42ad48fbb7))



### 🎨 User Interface

- Add "Apply CPU 0 fix on game launch" setting for ER, NR and DS3 ([158aedd](https://github.com/Hapfel1/er-save-manager/commit/158aedd53eec8f9d174e95f0387cde299d1a05eb))

- Fix performance issues ([04c441f](https://github.com/Hapfel1/er-save-manager/commit/04c441f8ad1e9b4be05521c15e2a9541306e9673))



### 📦 Dependencies

- Bump taiki-e/install-action in the github-actions group `[deps]` ([4f2a231](https://github.com/Hapfel1/er-save-manager/commit/4f2a231eeaf42e49b140a7ab47d158ddd6dbcbd7))



### Buld

- Lint ([181f197](https://github.com/Hapfel1/er-save-manager/commit/181f19778770e89527be95b464d155715fe0095d))



---
## 📦 Release 0.13.0
**Released:** April 02, 2026


### ✨ New Features

- Added Invasion Regions and ingame settings ([e674007](https://github.com/Hapfel1/er-save-manager/commit/e67400780232383d721e675b0085280d1af41bb5))

- Add other Fromsoft Games for SteamID Patching and Backup Manager ([b1d6e4b](https://github.com/Hapfel1/er-save-manager/commit/b1d6e4b5325172193f4c6fd4ad9b5f4bbbe5c527))

- Added "Move Bloodstain to player" button in the world state tab ([fed05c7](https://github.com/Hapfel1/er-save-manager/commit/fed05c7c55d8a8a4e06a6b2646c9b70b3ee56793))



### 🔧 Bug Fixes

- Fix event flag custom id toggle not creating backups ([7eae089](https://github.com/Hapfel1/er-save-manager/commit/7eae0894387cbef99f36912529d4a041e2e82a39))

- Fixed rendering issue in Appearance Tab popup window ([f8fc349](https://github.com/Hapfel1/er-save-manager/commit/f8fc3496e5b00fb547d3d1aae121b3c65ade97c0))

- Added change files ([b502a78](https://github.com/Hapfel1/er-save-manager/commit/b502a786ce1d3ff184d92b2c63ad7f3eca60f6bb))

- Lint ([2c6d07c](https://github.com/Hapfel1/er-save-manager/commit/2c6d07c608709e935df37d29949d1ea0a18ed4c9))

- Added correct functionality for steamid patching for each game ([6210337](https://github.com/Hapfel1/er-save-manager/commit/6210337fa7c9b01612eecb71baecec338d5d4bb5))

- Fixed Save Loading and Process detection for Non-ER games ([31c48d9](https://github.com/Hapfel1/er-save-manager/commit/31c48d90f717d909d7a38bb967a9c6b855d3d411))



### 🎨 User Interface

- Add Event Flag Export ([9378421](https://github.com/Hapfel1/er-save-manager/commit/9378421cd6452a11828594a33da56052ef5a4415))

- Added Great Rune and Rune Arc display ([61ac096](https://github.com/Hapfel1/er-save-manager/commit/61ac0962801aa6da40795486990666ad08634717))

- Fixed popup centering ([1ceb5dc](https://github.com/Hapfel1/er-save-manager/commit/1ceb5dcd25c62eff97eec2f2c767e93cb1c4aeac))

- Added warning when no apperance presets are saved to first save one in game ([580b149](https://github.com/Hapfel1/er-save-manager/commit/580b1490692dedbc6ca4d5c65e5f37449fb582be))

- Add MapID map for the known locations teleport feature ([ef62ebc](https://github.com/Hapfel1/er-save-manager/commit/ef62ebc55a6f29aa4e813b2a38a65ce9f5d43d64))



### 📦 Dependencies

- Bump the github-actions group with 3 updates `[deps]` ([61ca83d](https://github.com/Hapfel1/er-save-manager/commit/61ca83d842fe5ed53ed9920818b0b8bf41215ebc))



---
## 📦 Release 0.12.1
**Released:** March 23, 2026


### ✨ New Features

- Added Event Flag Torn Detection and Fix ([baa2948](https://github.com/Hapfel1/er-save-manager/commit/baa2948623073ab6b7fdb73bc3f7134361c087ab))



### 🔧 Bug Fixes

- Fixed last opened save location not working on Linux ([a6edd49](https://github.com/Hapfel1/er-save-manager/commit/a6edd4938e37a98267ba67a1a4e1f6eb9a2362b6))

- Add netman validation and corruption fixing after byteshift ([107a868](https://github.com/Hapfel1/er-save-manager/commit/107a86860244e634a16e79d1f46c05dcc83cdf9f))

- Fixed dlc flag detection + added apply button when only checking that checkbox ([ee22bd6](https://github.com/Hapfel1/er-save-manager/commit/ee22bd6101fc0e9d4db8dfd68586eb6d49a12dc2))

- Added Checksum validation for slots ([9928ad6](https://github.com/Hapfel1/er-save-manager/commit/9928ad6da245b0e08546b5ca4f9156cb24725c0a))

- Added event flags for npc quests and a tab for checking progress ([e9a17b8](https://github.com/Hapfel1/er-save-manager/commit/e9a17b8aa38ff9e448a4350179075fffae36b8d4))



### 🎨 User Interface

- Add button that links to discord server ([b3f8d8a](https://github.com/Hapfel1/er-save-manager/commit/b3f8d8a5c7b5e18f066d291c4fdaedbdbc902b05))

- Made popups from character_details appear centered over its parent ([8e1197f](https://github.com/Hapfel1/er-save-manager/commit/8e1197f4337875b70e785ea3710cca72f6b43794))



### 📦 Dependencies

- Bump the github-actions group with 2 updates `[deps]` ([4af85db](https://github.com/Hapfel1/er-save-manager/commit/4af85db09392fb47652ba599876aa7ee9dfd77c6))

- Bump taiki-e/install-action in the github-actions group `[deps]` ([b11b53d](https://github.com/Hapfel1/er-save-manager/commit/b11b53dc0dc879e61d19d7ca89d05115273a3487))



---
## 📦 Release 0.11.1
**Released:** March 14, 2026


### 🔧 Bug Fixes

- Fix: use data_start consistently
864a98e converted the offsets from slot-relative to absolute, but only
in the slot itself - all of the other scripts still expected it to have
been removed and would re-add the slot data offset back in, corrupting
the pointer and trashing the save slot. This removes the slot offset
addition from all of the places where the slot data offset is already
present in the slot object itself, preventing corruption ([93246a2](https://github.com/Hapfel1/er-save-manager/commit/93246a28010be7adfbfb560a4fd16da2699c703c))

- Fixed offsets being applied twice ([dc6a7da](https://github.com/Hapfel1/er-save-manager/commit/dc6a7da855b98758aa8a96a1585fb96363207037))



---
## 📦 Release 0.11.0
**Released:** March 13, 2026


### ✨ New Features

- Add NPC respawner ([270e0de](https://github.com/Hapfel1/er-save-manager/commit/270e0de67c14b9af76d6d75faa63ac0d076da558))

- Added known locations to the World State Tab for teleporting ([50ba6d7](https://github.com/Hapfel1/er-save-manager/commit/50ba6d73e99887c5b7a881e9c949784c61d9524a))

- Added more save file corruption detection and Fixes ([864a98e](https://github.com/Hapfel1/er-save-manager/commit/864a98ebf4d560131487b0d417c3518f69b6a258))



### 🔧 Bug Fixes

- Fixed window popup render issue on linux ([375375a](https://github.com/Hapfel1/er-save-manager/commit/375375a1f5beb9c5e2475aa892c3d34b5a0b7baa))

- Fixed SteamID Patcher AutoDetection ([cbdd7d4](https://github.com/Hapfel1/er-save-manager/commit/cbdd7d455bc2f352f829bc55e355741470da95b3))

- Fixed scrolling on Linux ([8fa53d5](https://github.com/Hapfel1/er-save-manager/commit/8fa53d5f6488bde378e4039fdd84f459c7cd8b89))

- Fixed Character Operations also copying ProfileSummary so that the character gets shown correctly instantly ([50c90c5](https://github.com/Hapfel1/er-save-manager/commit/50c90c5031bf2279b4c31261a181c96d40ec3d4e))



### 🎨 User Interface

- Made game running detection more clear and added a button to force quit the game ([9d7afcf](https://github.com/Hapfel1/er-save-manager/commit/9d7afcfa7639946b1b572b138e412c9d6c1d7131))

- Added new Toast info boxes to remove popup spam ([fe91822](https://github.com/Hapfel1/er-save-manager/commit/fe9182218e56ff7b1880403f1ee80abe60268f29))

- Remade Troubleshooting button to offer an Addon install for the standalone troubleshooter ([298e1a6](https://github.com/Hapfel1/er-save-manager/commit/298e1a6a20ec5433e46581ce80730ee3aa3dcf6a))

- Changed some info popups to be Toast notifications instead for a better UX ([27ee698](https://github.com/Hapfel1/er-save-manager/commit/27ee698a1555267f889cc337d3bb2d807bd367d7))

- Added character names next to the slot selections everywhere ([85be34e](https://github.com/Hapfel1/er-save-manager/commit/85be34ecacbf1c56e171263e159a4009c6bb279e))



---
## 📦 Release 0.10.1
**Released:** February 11, 2026


### 🔧 Bug Fixes

- Fix : fix character ops error ([9c60a4c](https://github.com/Hapfel1/er-save-manager/commit/9c60a4c5633608ada3b03a5f6666df2725f720b5))



---
## 📦 Release 0.10.0
**Released:** February 10, 2026


### ✨ New Features

- Added Auto-Backup Feature when booting up the game, changed backups to be zipped by default. ([12c562c](https://github.com/Hapfel1/er-save-manager/commit/12c562cb0fa3eb0258ac8943bc08cbafeb64a423))

- Added Character Browser ([c4199f7](https://github.com/Hapfel1/er-save-manager/commit/c4199f77a20d57d7a15545531e7e9b8f6c74913e))

- Add Convergence Support for the Character Browser ([b31d77f](https://github.com/Hapfel1/er-save-manager/commit/b31d77f0b258208d7edf229a2f268608a3a0581e))



### 🔧 Bug Fixes

- Fixed appimage build to include the custom lavender theme correctly ([69b044c](https://github.com/Hapfel1/er-save-manager/commit/69b044ceb1436dcf3c82b066c6f085919d82d61c))

- Added vpn checker in troubleshooting tab ([d81e4e9](https://github.com/Hapfel1/er-save-manager/commit/d81e4e9ef5f94f51a283ee8c651fbc7e00f83853))

- Added error for if the program is being run while zipped ([e6f5508](https://github.com/Hapfel1/er-save-manager/commit/e6f5508a370671feba144cd5e3e4c9876461360a))

- Fix steamdeck resolution issue ([40188fa](https://github.com/Hapfel1/er-save-manager/commit/40188fa015e5ac607b9b6ed31f95abd729090715))

- Fixed wrong cnv save detection ([ebaecf7](https://github.com/Hapfel1/er-save-manager/commit/ebaecf790dc366bdd81f97b8285ef359d4d19255))

- Fixed error when copying characters because of invalid filename characters, added sanitization ([efa87ad](https://github.com/Hapfel1/er-save-manager/commit/efa87ad8fecca4b0a2214add81760e3bf5febf2a))

- Made opening links work on Linux ([3d33715](https://github.com/Hapfel1/er-save-manager/commit/3d337153c245ed5576aa8136d7fc59b70b1af1ea))

- Fixed transferring characters between Save Files to correctly update Profile Summary and fixed an offset tracking error ([e4de080](https://github.com/Hapfel1/er-save-manager/commit/e4de08040c2abe1ff0abcec356133a79bd6bc31b))



### 🎨 User Interface

- Made autobackup more clear and easier to use ([f11c910](https://github.com/Hapfel1/er-save-manager/commit/f11c910fd91849483694d1f1fe334fce4dab6aac))

- Revamped UI to work better for small resolution displays ([9f13ef9](https://github.com/Hapfel1/er-save-manager/commit/9f13ef99178c8bc900bc0cdbb4c2ef4f2337e39d))



### 📖 Documentation

- Updated TODO ([8c165dd](https://github.com/Hapfel1/er-save-manager/commit/8c165dd5b27212585c76555603ef425ae83eef68))



### Buld

- Edit todo ([e14dd3e](https://github.com/Hapfel1/er-save-manager/commit/e14dd3ee7d0181deb1f85170307865e5dfbdfa9e))



---
## 📦 Release 0.9.0
**Released:** February 03, 2026


### ✨ New Features

- Added export to JSON preset selection ([a72d783](https://github.com/Hapfel1/er-save-manager/commit/a72d783b724798d24d30fd786a282f675c16abba))



### 🔧 Bug Fixes

- Correct case sensitivity for theme path on Linux ([7c2a48a](https://github.com/Hapfel1/er-save-manager/commit/7c2a48a698216e4dcfcdd7692078dba127d65626))

- Fixed event flags being written incorrectly ([cc49186](https://github.com/Hapfel1/er-save-manager/commit/cc491863ecdb44fbb60599d33b21d7115b8913c3))

- Fixed save file backup functionality ([f44c7e6](https://github.com/Hapfel1/er-save-manager/commit/f44c7e65d44fd8688068631fdcf9f7fde79921b1))

- Fixed Character operation issues ([70080fb](https://github.com/Hapfel1/er-save-manager/commit/70080fbaba8c68246ad5e796f3a6698b9969cfdb))

- Fixed info message popups appearing behind main window ([69162ad](https://github.com/Hapfel1/er-save-manager/commit/69162ad08cb60707c0f982b923e8852ce1c1cc56))



---
## 📦 Release 0.8.0
**Released:** February 02, 2026


### ✨ New Features

- Added version checker to notify users of new update ([9d49382](https://github.com/Hapfel1/er-save-manager/commit/9d49382af93792e0762eb4572c94c02ecf41ea17))

- Add Troubleshooter for checking game und save file related issues ([4eb53b7](https://github.com/Hapfel1/er-save-manager/commit/4eb53b7c073e6d412fb5bcd48314f69b124829bf))



### 🔧 Bug Fixes

- Fixed SteamDeck not showing Preset Browser correctly bc of SSL errors ([c6496ce](https://github.com/Hapfel1/er-save-manager/commit/c6496ce5fd604f41e2425caf74d23e23c7826ce3))



---
## 📦 Release 0.7.4
**Released:** January 31, 2026


### 🔧 Bug Fixes

- Fixed JSON import error msg ([aa67a3b](https://github.com/Hapfel1/er-save-manager/commit/aa67a3b5617b5cfe063668b774227a7dad34795c))



### 🎨 User Interface

- Change default theme to dark ([25a2a64](https://github.com/Hapfel1/er-save-manager/commit/25a2a64c291844c67648573972d953f3ea942c26))



---
## 📦 Release 0.7.3
**Released:** January 30, 2026


### ✨ New Features

- Add ng+ editor in character info tab ([b79a135](https://github.com/Hapfel1/er-save-manager/commit/b79a1358710cd42716ffcdcb5b666e7c1dc88221))



### 🔧 Bug Fixes

- Changed image display in the preset browser to always display the original image's resolution ([5f5d609](https://github.com/Hapfel1/er-save-manager/commit/5f5d609bc72574fde4ad38ddc46a7cc2f40485bd))



### 🎨 User Interface

- Make save fixer description more clear and add auto loading upon selecting a save file ([3df841b](https://github.com/Hapfel1/er-save-manager/commit/3df841b162422759694165893adb71c99dc9885b))

- Made all message boxes custom and improved the messagebox module ([8db333e](https://github.com/Hapfel1/er-save-manager/commit/8db333e84a379c42fb7f3be1107643456a20c015))

- Centered all popups to be in the middle of the parent's window ([e04cc7d](https://github.com/Hapfel1/er-save-manager/commit/e04cc7d3d820dad961f0875ea938eac28bc516c7))



### 📖 Documentation

- Update TODO ([6f0fd88](https://github.com/Hapfel1/er-save-manager/commit/6f0fd88b372f6c650d6a8c9064822c3027c009ac))



---
## 📦 Release 0.7.2
**Released:** January 30, 2026


---
## 📦 Release 0.7.1
**Released:** January 28, 2026


### 🔧 Bug Fixes

- Fixed error message pop-up when no actual error happened ([0ce4231](https://github.com/Hapfel1/er-save-manager/commit/0ce42314ce6e2e6cda7ff7dd2fd57ce0fa503d23))



---
## 📦 Release 0.7.0
**Released:** January 28, 2026


### ✨ New Features

- Add DLC flag clearing with conditional UI and teleport integration ([9b2c7b9](https://github.com/Hapfel1/er-save-manager/commit/9b2c7b94ff311220969a3a49a437e297222867aa))



### 🔧 Bug Fixes

- Made all tabs scrollable, fixed typo ([320f047](https://github.com/Hapfel1/er-save-manager/commit/320f0474fc2590e0cf6b6dd22ea69bd4e8c99c43))

- Format & lint ([155c326](https://github.com/Hapfel1/er-save-manager/commit/155c3262a01242143a48e6a294af7d7e6ccd9f66))



### 🎨 User Interface

- Fixed color issue in bright mode with character editor tab ([448b08d](https://github.com/Hapfel1/er-save-manager/commit/448b08d70e5a56a4336f9b8829453ddace07c78b))



---
## 📦 Release 0.6.2
**Released:** January 27, 2026


### 🔧 Bug Fixes

- Fixed workflow version numbering ([201ec8d](https://github.com/Hapfel1/er-save-manager/commit/201ec8da2587bf7d9a93a7983ef155355a39319d))



---
## 📦 Release 0.6.1
**Released:** January 27, 2026


### 🔧 Bug Fixes

- Fixed version  bumping to include manifest and version info file ([1af05de](https://github.com/Hapfel1/er-save-manager/commit/1af05de2a757b62618836b5f767e4c97b8c309e9))



---
## 📦 Release 0.6.0
**Released:** January 27, 2026


### ✨ New Features

- Apply dark theme to character editor and fix CTkMessageBox calls `[ui]` ([15cfbb4](https://github.com/Hapfel1/er-save-manager/commit/15cfbb47c894e3174b73be6ddb1736e427911a3a))

- Community preset system with metrics, voting, and reporting ([d2f5a0a](https://github.com/Hapfel1/er-save-manager/commit/d2f5a0ab028f653d3dba11edddee957ed120049f))

- Cross-platform save file detection and Linux steam path improvements ([f4954a2](https://github.com/Hapfel1/er-save-manager/commit/f4954a247f6d466f2205968e34b3130ece91ffe3))



### 🔧 Bug Fixes

- Improve save file loading and compatdata warnings ([2d3332c](https://github.com/Hapfel1/er-save-manager/commit/2d3332c28396d52845be06e66db294817b4d2db3))

- Format & lint ([6112d26](https://github.com/Hapfel1/er-save-manager/commit/6112d26d79c5c267e2b689bc6e25b82cdacbe8db))

- Fixed issues when running the appimage on linux ([427011a](https://github.com/Hapfel1/er-save-manager/commit/427011a39eb16c964eb3feaa1a56868a102f28c7))

- Fix: linux tab rendering fixes
build: added logging to find out issue with appearance browser ([7737830](https://github.com/Hapfel1/er-save-manager/commit/77378301ae20f22c277887f9035c04e81f3d4e6c))

- Format & lint ([6281eb0](https://github.com/Hapfel1/er-save-manager/commit/6281eb028873de252bb8665eb954da589d2343ba))

- Fix: Fixed PIL/Tkinter ingegration for Linux
Fixed Resource loading
Fixed "grab failed" issues ([f9cf8a3](https://github.com/Hapfel1/er-save-manager/commit/f9cf8a318f90d1121c84881337314e19b1859cc8))

- Fixed eventflag binary search tree text file loading on linux ([e58634c](https://github.com/Hapfel1/er-save-manager/commit/e58634c1193b9e335000169876e7e23fc36baa89))

- Fixed correct resources import ([6b58161](https://github.com/Hapfel1/er-save-manager/commit/6b581618baba8c33c160c332d032b409942d0728))



### 🎨 User Interface

- Enhance preset browser and application UI ([2a4bfaa](https://github.com/Hapfel1/er-save-manager/commit/2a4bfaa9b1588344fb956bf69d2c05142185a785))



### 📖 Documentation

- Complete documentation rewrite with feature status and architecture ([25a377a](https://github.com/Hapfel1/er-save-manager/commit/25a377a4bf8fdd4d19917e256a8df6880e5400eb))

- Fixed documentation ([0936903](https://github.com/Hapfel1/er-save-manager/commit/09369034d090ad99e97170d343d187d83e76ad6e))



### ⚡ Performance Improvements

- Optimize preset browser loading and caching ([7bfe8b6](https://github.com/Hapfel1/er-save-manager/commit/7bfe8b6e09592ad2a27ecfe3c150c5a85d33fe1d))



### 🧹 Maintenance

- Fix gitignore to track source data and fix region_ids_map ([f3f10a0](https://github.com/Hapfel1/er-save-manager/commit/f3f10a0d2148277bba22faeaf003a86c738f1c39))



---
## 📦 Release 0.5.1
**Released:** January 24, 2026


### 🔧 Bug Fixes

- Fixed import/export ([5b43c5f](https://github.com/Hapfel1/er-save-manager/commit/5b43c5f6b69850fdd39bc0398607810d5b3eaef0))

- Format & lint ([62f285f](https://github.com/Hapfel1/er-save-manager/commit/62f285f9fb5ccc7bd592cab9c46b205cc7de1208))



---
## 📦 Release 0.5.0
**Released:** January 24, 2026


### ✨ New Features

- Major UI improvements and bug fixes ([ff797d2](https://github.com/Hapfel1/er-save-manager/commit/ff797d2a5136d72f5388c41cf2ee4555a07b5a22))

- Complete SteamID patcher with custom URL resolution `[steamid]` ([5693746](https://github.com/Hapfel1/er-save-manager/commit/56937465fda1f2f53b6bb1831a1ee4c2e7ef8dd4))

- Implement comprehensive event flags and gestures systems ([2cfa82d](https://github.com/Hapfel1/er-save-manager/commit/2cfa82df244a41df1cacbba657d34d021eeb54f3))

- Implement boss respawn function (not finished) ([31f0af3](https://github.com/Hapfel1/er-save-manager/commit/31f0af34b8c95bf8f8b6966b6ea531800868ce10))

- Implement complete community character preset browser system `[ui]` ([0473d4d](https://github.com/Hapfel1/er-save-manager/commit/0473d4d51589a3c241f8e3da5a004ae110d729a2))



### 🔧 Bug Fixes

- Small removal ([22ad8e0](https://github.com/Hapfel1/er-save-manager/commit/22ad8e089e83a784ce80410020d15cbc053e9770))

- Fix: removed temporary testing buttons
docs: updated tooltips for boss respawner ([4e1610c](https://github.com/Hapfel1/er-save-manager/commit/4e1610c7111bbb4ce8fa217da0d9fe66a6b77ca1))

- Lint % format ([2e4ca4c](https://github.com/Hapfel1/er-save-manager/commit/2e4ca4cbfc45afff3fcb8b04a76f2c016a76e29b))

- Fix: small fixes for UI
fix: fix appearance browser + add workflow for submission ([f10476e](https://github.com/Hapfel1/er-save-manager/commit/f10476efd0983468b788ab01a65e5f28e23dbe55))



### 📖 Documentation

- Updated TODO.md ([9673787](https://github.com/Hapfel1/er-save-manager/commit/96737878702ced21cda66e8a4da753b759f47e9f))

- Updated TODO ([34cd7d2](https://github.com/Hapfel1/er-save-manager/commit/34cd7d2110a8a62b4cc5c6745d43f41368491a3d))



---
## 📦 Release 0.4.1
**Released:** January 23, 2026


### 🔧 Bug Fixes

- License format in pyproject.toml to combat deprecation warning ([00c9eed](https://github.com/Hapfel1/er-save-manager/commit/00c9eed93219f627ddb843aaac646e40ea919c6b))

- Fix deprecation issue with license ([c4834ef](https://github.com/Hapfel1/er-save-manager/commit/c4834ef1f9de5aa93276a7e442312be44f1f5d02))



---
## 📦 Release 0.4.0
**Released:** January 18, 2026


### ✨ New Features

- Add modular UI components ([c2f1997](https://github.com/Hapfel1/er-save-manager/commit/c2f1997664666a612bf72b0f48a8401b14a97cf8))

- Add modular GUI coordinator ([3c91776](https://github.com/Hapfel1/er-save-manager/commit/3c91776ffbac9357366b16a0b1504866ed3bf9c7))

- Add item database for user-friendly names ([b78fc48](https://github.com/Hapfel1/er-save-manager/commit/b78fc48571ad18cb7edc44da4afa0e06ac7db0f5))



### 🔧 Bug Fixes

- Fixed cli to integrate new ui modules ([61a8b6d](https://github.com/Hapfel1/er-save-manager/commit/61a8b6dd03c161e98ed0229dffc28f6985467083))

- Update parser for GUI compatibility ([67d2019](https://github.com/Hapfel1/er-save-manager/commit/67d2019358077caa02e09d220c2f1feda30adf66))

- Format and lint ([37de52f](https://github.com/Hapfel1/er-save-manager/commit/37de52fcb3384ab3c8cd817c96221e67c948b6db))



### 🧹 Maintenance

- Update TODO and backup original GUI ([bc3bc46](https://github.com/Hapfel1/er-save-manager/commit/bc3bc463fb8e1e3746ddadc7aeec0aad8a1cf64b))



---
## 📦 Release 0.3.0
**Released:** January 17, 2026


### ✨ New Features

- Add character operations module with dynamic offset tracking ([d8d58f8](https://github.com/Hapfel1/er-save-manager/commit/d8d58f8f241bde751c67f886d985cdf0876b63c8))

- Implement dynamic offset tracking in save parser ([d77305e](https://github.com/Hapfel1/er-save-manager/commit/d77305ee0952193ad36ec053a9c35838e3f732aa))



### 🎨 User Interface

- Redesign character management with operation dropdown ([609a478](https://github.com/Hapfel1/er-save-manager/commit/609a478c3ab395292940de0c9bccaa2b499ccf0f))



### 📖 Documentation

- Updated TODO.md ([2115d99](https://github.com/Hapfel1/er-save-manager/commit/2115d99d5f78fc9208f7648c49990bd1708ba443))



---
## 📦 Release 0.2.1
**Released:** January 17, 2026


### 🔧 Bug Fixes

- Convert all relative imports to absolute ([5ea6078](https://github.com/Hapfel1/er-save-manager/commit/5ea607892896cabe1e5ac3b37d784dc891c1669d))



### 📖 Documentation

- Add TODO file with feature implementation roadmap ([e28e577](https://github.com/Hapfel1/er-save-manager/commit/e28e57723929dfde22919d109195c85374e0eaf9))



---
## 📦 Release 0.2.0
**Released:** January 17, 2026


### ✨ New Features

- Add GUI launcher and fix Windows executable ([12f4911](https://github.com/Hapfel1/er-save-manager/commit/12f4911bd141bb660d13bd276d0d5aa8288259d4))



### 🔧 Bug Fixes

- Use absolute import for cx_Freeze compatibility ([ecabaf3](https://github.com/Hapfel1/er-save-manager/commit/ecabaf3834da0cccdec487aae9c2d52e69a1a55b))

- Convert all relative imports to absolute for cx_Freeze compatibility ([cf39803](https://github.com/Hapfel1/er-save-manager/commit/cf3980334b81b4cfdbb82efee0b115da3762b2c4))

- Test auto release trigger ([15f80bc](https://github.com/Hapfel1/er-save-manager/commit/15f80bcbb76495b7db7907b0ed96e55d4b550785))

- Release workflow safety check and changelog extraction ([2998705](https://github.com/Hapfel1/er-save-manager/commit/299870540cf9b922bd07cf8a80073d0407d8f564))

- Correct PR URL in cliff.toml template ([e4b2d56](https://github.com/Hapfel1/er-save-manager/commit/e4b2d564e1d73cd6dbd338f7f98abbb1cbb18283))



### 🧹 Maintenance

- Re-trigger release for 0.1.1 ([765b99d](https://github.com/Hapfel1/er-save-manager/commit/765b99d65c89c5cb5851025640ea7ec86616d1c3))

- Update repo URLs to upstream (Hapfel1) ([4402930](https://github.com/Hapfel1/er-save-manager/commit/4402930cf948f4b64a2adbe28fd8c7a113d4c69f))



---
## 📦 Release 0.1.0
**Released:** January 17, 2026


### ✨ New Features

- Added release workflow ([1020635](https://github.com/Hapfel1/er-save-manager/commit/1020635c64bc24f759f08f96898aad32f645a44b))

- Added gui, implemented functions partially ([252b1a7](https://github.com/Hapfel1/er-save-manager/commit/252b1a7f15b8dc9ed082625f408870f05c7399ef))

- Feat: add new gui features (templates for further
implementation) ([19bee2c](https://github.com/Hapfel1/er-save-manager/commit/19bee2ccc54139c84a885afd66f9ff4be65cfc57))

- Add automatic release workflow and build scripts ([a3fade6](https://github.com/Hapfel1/er-save-manager/commit/a3fade69b5c24e72567552adfadf474dd57f9480))



### 🔧 Bug Fixes

- Edited readme correctly ([08d07c8](https://github.com/Hapfel1/er-save-manager/commit/08d07c8e6e59cae477ffd25d1bbb93287148a154))

- README ([68f2635](https://github.com/Hapfel1/er-save-manager/commit/68f263548542be47e011932fe7070e6cc8a9d74f))

- Lint and format ([156bdc6](https://github.com/Hapfel1/er-save-manager/commit/156bdc62093d20b8ca476366286b5e28562e035a))

- Fix import ([856ca9c](https://github.com/Hapfel1/er-save-manager/commit/856ca9c31fb8168775fbe3739ac7b57702448c2d))

- Set executable permissions for shell scripts ([ef832ac](https://github.com/Hapfel1/er-save-manager/commit/ef832ac9777de8880a3191c223a285aad32778eb))

- Fix ci.yml ([9b1d27a](https://github.com/Hapfel1/er-save-manager/commit/9b1d27ab844f746377362b23354ee1da1bfee629))



### 🧹 Maintenance

- Repo URLs in cliff.toml for upstream ([e889185](https://github.com/Hapfel1/er-save-manager/commit/e889185aa27086d6a4de2d1a25528b3a5d5ee890))



---
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

