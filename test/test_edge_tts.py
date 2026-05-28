"""Example showing how to use use .stream() method to get audio chunks
and feed them to SubMaker to generate subtitles"""

import asyncio

import edge_tts

TEXT = "أُحِبُّ أَحْيَانًا أَنْ أَبْتَعِدَ قَلِيلًا عَنْ ضَجِيجِ الْحَيَاةِ الْيَوْمِيَّةِ، فَأَجْلِسُ فِي مَكَانٍ هَادِئٍ مَعَ فِنْجَانِ قَهْوَةٍ وَكِتَابٍ جَمِيلٍ، لِأَنَّ تِلْكَ اللَّحَظَاتِ الْبَسِيطَةَ تَمْنَحُنِي شُعُورًا بِالرَّاحَةِ وَتُسَاعِدُنِي عَلَى التَّفْكِيرِ بِهُدُوءٍ وَصَفَاءٍ."
VOICE = "ar-EG-SalmaNeural"
OUTPUT_FILE = "test.mp3"
SRT_FILE = "test.srt"


async def amain() -> None:
    """Main function"""
    communicate = edge_tts.Communicate(TEXT, VOICE)
    submaker = edge_tts.SubMaker()
    with open(OUTPUT_FILE, "wb") as file:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                file.write(chunk["data"])
            elif chunk["type"] in ("WordBoundary", "SentenceBoundary"):
                submaker.feed(chunk)

    with open(SRT_FILE, "w", encoding="utf-8") as file:
        file.write(submaker.get_srt())


if __name__ == "__main__":
    asyncio.run(amain())