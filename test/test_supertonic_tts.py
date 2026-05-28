from supertonic import TTS

tts = TTS(auto_download=True)
style = tts.get_voice_style(voice_name="M1")
text = "أُحِبُّ أَحْيَانًا أَنْ أَبْتَعِدَ قَلِيلًا عَنْ ضَجِيجِ الْحَيَاةِ الْيَوْمِيَّةِ، فَأَجْلِسُ فِي مَكَانٍ هَادِئٍ مَعَ فِنْجَانِ قَهْوَةٍ وَكِتَابٍ جَمِيلٍ، لِأَنَّ تِلْكَ اللَّحَظَاتِ الْبَسِيطَةَ تَمْنَحُنِي شُعُورًا بِالرَّاحَةِ وَتُسَاعِدُنِي عَلَى التَّفْكِيرِ بِهُدُوءٍ وَصَفَاءٍ."
wav, duration = tts.synthesize(text, voice_style=style, lang="ar")

tts.save_audio(wav, "output.wav")
print(f"Generated {duration:.2f}s of audio")