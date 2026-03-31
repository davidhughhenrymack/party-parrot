# Party Parrot Venue Conventions

- Store venue distances in meters in the database and runtime snapshots.
- The venue editor may show floor width/depth in feet, but it must convert to meters before saving.
- Venue/world axes are:
  - `x`: audience-left to audience-right, with audience-left negative and centerline `0`
  - `y`: downstage/audience to upstage/DJ, with upstage negative and center `0`
  - `z`: height above the floor in meters
- Floor scene objects are centered at `x = 0`, `y = 0`.
- Fixture and scene-object rotations are stored in radians as `rotation_x`, `rotation_y`, `rotation_z`.
- Party Parrot runtime is the source of truth for fixture body shapes and beam conventions. When updating editor visuals, match:
  - generic fixtures: shallow rectangular body
  - moving heads: short base plus deeper moving head body
  - motionstrips: long low bar body
  - lasers: cube body
- Beam/cone direction conventions must stay aligned with Party Parrot runtime rendering, not ad hoc editor geometry.
- DJ booth defaults should use real-world dimensions:
  - DJ height: `1.8288m` (`6ft`)
  - DJ table: `2.4384m` wide, `1.2192m` deep, `1.0668m` tall
