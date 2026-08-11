/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */

/*
 * Stub for `sharp`, substituted via the "overrides" entry in package.json.
 *
 * `sharp` is an optionalDependency of `next`, used only for runtime
 * `next/image` optimization. This app does a static export with
 * `images.unoptimized: true` and never imports `next/image`, so sharp is dead
 * weight -- but it pulls in `@img/sharp-libvips-*`, which is LGPL-3.0-or-later
 * and therefore not on Amazon's pre-approved license list.
 *
 * Throwing here rather than silently no-oping means that if anything ever does
 * start depending on sharp, the build fails loudly instead of shipping broken
 * image handling.
 */
function sharp() {
  throw new Error(
    "sharp is intentionally stubbed out (see projects/frontend/stubs/sharp/index.js). " +
      "This app uses a static export with unoptimized images and does not need it."
  );
}

module.exports = sharp;
module.exports.default = sharp;
