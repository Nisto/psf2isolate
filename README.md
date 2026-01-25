# psf2isolate
Isolates audio samples in mini/PSF2 (Portable Sound Format for PlayStation 2) files, which gives you the power to hear exactly how each sample is played, create your own mixes, and more. Samples are automatically located and dumped to separate miniPSF2 files.

For isolating PSF1 files, see [psfisolate](https://github.com/Nisto/psfisolate).

## Usage

*On systems where supported, you can simply* ***drag-n-drop a PSF2 file onto the script***. Otherwise, pass a file via terminal, e.g.:

```sh
python3 psf2isolate.py bgm_123.minipsf2
python3 psf2isolate.py town_theme.psf2
```

**NOTE:** If a mini/PSF2 loads its soundbank from a shared filesystem (e.g. a psf2lib), you may be prompted to confirm/enter which soundbank to target. In such cases, a best guess ("default") may be provided; if the names are correct you may simply press Enter (leave blank) to proceed with the suggested names. Example:

```txt
* Loading PSF2...

* Loaded PSF2 virtual filesystem:
  BGM50000.BD
  BGM50000.HD
  < +151 more files >
  libsd.irx
  psf2.irx

* Multiple HD/BD soundbank files detected - confirm names:
  HD [default: BGM50123.HD]:
  BD [default: BGM50123.BD]:

* Writing psf2lib to: ...
* Writing minipsf2 for isolated sample 0 to: ...
* Writing minipsf2 for isolated sample 1 to: ...
* Writing minipsf2 for isolated sample 2 to: ...
```

## Limitations

As this is still in an early stage of development, for now only standard Sony (SCEI) HD/BD soundbanks are supported. If there's enough demand, universal soundbank support (via heuristics) will be considered.

## FAQ

#### Q: Some output PSFs are completely silent, missing audio or contain gaps?
**A:** There are numerous possible reasons for this, not limited to:
1. The sample is unused (please understand the tool has no knowledge of which samples are un-/used)
2. The sample is part of a multi-sample instrument (e.g. piano, guitar, etc.) and only some of the samples are triggered by the music sequence
3. The input file/game may use shared soundbanks, some of which may only be used for other music sequences
4. Your PSF2 decoder erroneously removed audio (if you use HighlyExperimental, make sure to disable silence-suppression settings)
5. The tool has a bug (least likely as most silencing/isolation bugs have been found and fixed)

## Support ❤️

As of Septemer 2025, I am permanently out of work due to company bankruptcy. This has had a significant impact on my freedom and ability to spend as much time working on my projects, especially due to electricity bills. I don't like asking for favors or owing people anything, but if you do like this work and happen to have some funds to spare, donations are always imensely appreciated. All of your contributions goes towards essential everyday expenses. Every little bit helps! Thank you ❤️

**PayPal:** https://paypal.me/nisto7777  
**Buy Me a Coffee:** https://buymeacoffee.com/nisto  
**Bitcoin:** 18LiBhQzHiwFmTaf2z3zwpLG7ALg7TtYkg
