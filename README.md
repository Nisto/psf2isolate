# psf2isolate
Isolates audio samples in mini/PSF2 (Portable Sound Format for PlayStation 2) files, which gives you the power to hear exactly how each sample is played, create your own mixes, and more. Samples are automatically located and dumped to separate miniPSF2 files.

For isolating PSF1 files, see [psfisolate](https://github.com/Nisto/psfisolate).

## Usage

On systems where supported, you can simply drag-n-drop a PSF2 file onto the script. If not, pass a mini/PSF2 via CLI (command-line).

## Limitations

As this is still in an early stage of development, for now only standard Sony (SCEI) HD/BD soundbanks are supported. If there's enough demand, universal soundbank support (via heuristics) will be considered.

## FAQ

#### Q: Some output PSFs are completely silent or contain gaps?
**A:** There are numerous possible reasons for this. If only some of the files are silent, the game may use shared sound banks, where the song only uses some of the samples (please understand that the tool has no knowledge of which samples are actually used). Also, if the soundbank contains a multi-sample instrument that is being played, only some of the samples may actually be triggered by the music sequence. If there appears to be "gaps", it's most likely because different notes trigger different samples within the same instrument. It's important to note the distinction between **samples** and *instruments*.

## Support ❤️

As of Septemer 2025, I am permanently out of work due to company bankruptcy. This has had a significant impact on my freedom and ability to spend as much time working on my projects, especially due to electricity bills. I don't like asking for favors or owing people anything, but if you do like this work and happen to have some funds to spare, donations are always imensely appreciated. All of your contributions goes towards essential everyday expenses. Every little bit helps! Thank you ❤️

**PayPal:** https://paypal.me/nisto7777  
**Buy Me a Coffee:** https://buymeacoffee.com/nisto  
**Bitcoin:** 18LiBhQzHiwFmTaf2z3zwpLG7ALg7TtYkg
