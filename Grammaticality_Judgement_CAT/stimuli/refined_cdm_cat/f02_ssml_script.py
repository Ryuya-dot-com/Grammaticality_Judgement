"""F02 SSML override script.

For the 6 F02 U items (P007U-P012U), TTS systems may auto-coarticulate
"a + vowel-initial noun" to "an + vowel-initial". Use SSML phoneme
override to force /ə/ pronunciation of "a" + brief pause + vowel-initial noun.

Usage:
    python3 f02_ssml_script.py

Outputs SSML strings to stdout; pipe to Amazon Polly or save to disk.
For OpenAI tts-1 (no SSML support), manual audio splicing is required.
"""
import pandas as pd
import re

CSV = "stimulus_master_cdm_cat_v3.csv"

def make_ssml(target_text: str) -> str:
    """Insert phoneme override for 'a' before vowel-initial noun."""
    # Pattern: " a [vowel-initial word]" → " <phoneme>a</phoneme> <word>"
    pattern = re.compile(r"\ba\s+([aeiouAEIOU]\w+)")
    def repl(m):
        return f'<phoneme alphabet="ipa" ph="ə">a</phoneme> <break time="100ms"/> {m.group(1)}'
    return f"<speak>{pattern.sub(repl, target_text)}</speak>"

if __name__ == "__main__":
    df = pd.read_csv(CSV)
    f02_u = df[(df['family_id']=='F02') & (df['version']=='U')]
    print("# F02 U items — SSML for audio generation")
    print("# Use with Amazon Polly Joanna (Neural) for best results")
    print()
    for _, row in f02_u.iterrows():
        ssml = make_ssml(row['target_text'])
        print(f"# {row['item_id']}: {row['target_text']}")
        print(f"# SSML:")
        print(ssml)
        print()

# Example expected output for P007U:
#   <speak>
#     Sara ate <phoneme alphabet="ipa" ph="ə">a</phoneme> <break time="100ms"/> orange quickly.
#   </speak>
