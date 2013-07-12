// Copyright (c) 2013 The Chromium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

'use strict';

base.requireStylesheet('tracing.tracks.spacing_track');

base.exportTo('tracing.tracks', function() {
  /**
   * @constructor
   */
  var SpacingTrack = ui.define('spacing-track', tracing.tracks.DrawableTrack);

  SpacingTrack.prototype = {
    __proto__: tracing.tracks.DrawableTrack.prototype,

    decorate: function(viewport) {
      tracing.tracks.DrawableTrack.prototype.decorate.call(this, viewport);
      this.classList.add('spacing-track');
    },

    draw: function(viewLWorld, viewRWorld) {
    }
  };


  return {
    SpacingTrack: SpacingTrack
  };
});