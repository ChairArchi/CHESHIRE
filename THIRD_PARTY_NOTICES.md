# External dependencies and distribution boundaries

- COMPAS 2.15.1 is an external Python dependency and is not vendored.
- pythonnet 3.0.5 is an optional external dependency and is not vendored.
- Mola/HDMola is an optional external runtime integration.
- CHESHIRE redistributes no Mola/HDMola binary or upstream source.
- Users must supply their own compatible external DLL where required.
- Task26 review uses optional pyrender 0.1.45, trimesh 5.1.1, Pillow 11.3.0,
  pyglet 2.1.16 and their runtime dependencies. They are installed externally;
  no package source/binary is bundled in the repository or review archives.

The repository excludes environments, output/local_settings.json and review
archives. Technical compatibility does not grant third-party redistribution
permission. No license for HDMolaGH is asserted. CHESHIRE project licensing
remains intentionally undecided.
