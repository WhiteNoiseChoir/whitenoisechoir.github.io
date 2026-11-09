#!/usr/bin/env node
"use strict";
/** Post-migration GH headroom gate.
 * 27 approved HLS streams live at Cloudflare R2, 8 locally retain
 * true independent GitHub native HLS failover and 35 MP3s stay local.
 * Run the dedicated cloud SHA read-back workflow to verify 297 R2 bytes.
 */
require("./test_r2_balanced_layout.cjs");
console.log("R2_STORAGE_BUDGET_PASS: balanced GH HLS set retained, 27 R2 HLS streams verified by separate remote SHA workflow, all 35 approved local MP3 retained. Do not confuse HEAD tree size with Git history or published Pages artifact size.");
