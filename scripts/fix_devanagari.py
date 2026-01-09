#!/usr/bin/env python3
"""
Fix corrupted Devanagari characters in extracted Hindi textbook.

The PDF has font encoding issues where conjunct characters (ligatures)
are mapped to incorrect Unicode code points. This script maps them back.
"""

import os
import re
from pathlib import Path

# Character mapping: corrupted -> correct
# Built by analyzing extracted text against expected Hindi
CHAR_MAP = {
    # Common words with full replacements (most reliable)
    'मœ': 'मैं',           # I
    'šँ': 'हूँ',           # am
    'hœ': 'हैं',           # are (plural)
    'Šआ': 'हुआ',          # happened/was
    'Šई': 'हुई',          # happened/was (fem)
    'Šए': 'हुए',          # happened/was (plural/oblique)
    'Ɛा': 'क्या',         # what/question marker
    'Ɛों': 'क्यों',        # why
    'Ůताप': 'प्रताप',      # Pratap (name)
    'Ůकाश': 'प्रकाश',      # Prakash (name)
    'Ůेम': 'प्रेम',        # Prem (name) / love
    'नमˑे': 'नमस्ते',      # namaste
    'िह̢दुˑानी': 'हिंदुस्तानी',  # Indian
    'िहȽी': 'हिंदी',       # Hindi
    'अँŤेज़': 'अंग्रेज़',    # English (person)
    'अǅा': 'अच्छा',       # good/okay
    'माŜित': 'मारुति',     # Maruti
    'जमŊन': 'जर्मन',       # German
    'शुिŢया': 'शुक्रिया',   # thank you
    'ɗार': 'प्यार',        # love
    'Ŝकता': 'रुकता',       # stops
    'Ŝकना': 'रुकना',       # to stop

    # Conjunct consonants (क्ष, त्र, ज्ञ, श्र, etc.)
    'Ť': 'ग्र',           # gra
    'ũ': 'त्र',           # tra
    'ʹ': 'श्र',           # shra
    'ʷ': 'श्व',           # shva
    'ʃ': 'म्म',           # mma
    'ˑ': 'स्त',           # sta
    'ˁ': 'स्थ',           # stha
    '˓': 'स्त्र',          # stra
    'Ŝ': 'रु',            # ru
    'ȏ': 'त्म',           # tma
    'Ő': 'ें',            # en (vowel sign)
    'Ų': 'म्र',           # mra
    'ʝ': 'ल्म',           # lma
    'Ǆ': 'च्च',           # ccha
    'ǅ': 'च्छ',           # chha
    'Ž': 'द्ध',           # ddha
    'Ǝ': 'द्द',           # dda
    'Ɏ': 'न्ह',           # nha
    'ɗ': 'प्य',           # pya
    'ő': 'र्क',           # rka
    'Ŋ': 'र्म',           # rma
    'İ': 'खि',           # khi (or ख़ि)
    'Ȩ': 'द्या',          # dya
    'ȅ': 'त्त',           # tta
    'ʻ': 'फ़्',           # fa with halant
    'Ɛ': 'क्य',           # kya
    'ǁ': 'य्य',           # yya
    'Ŵ': 'श्रु',          # shru
    'ʷ': 'श्व',           # shva
    '̢': 'न्द',           # nda
    'Ɩ': 'ष्ट',           # shta
    'Ȼ': 'क्त',           # kta
    '̾': 'स्',            # sa with halant
    'Ⱥ': 'ड्ड',           # dda (hard)

    # Vowel signs and matras
    'œ': 'ैं',            # ain matra
    'Ő': 'ें',            # en matra

    # Numbers and punctuation fixes
    '०': '0',            # if needed

    # Common word fixes
    'बǄे': 'बच्चे',        # children
    'बǄा': 'बच्चा',        # child
    'बǄों': 'बच्चों',      # children (oblique)
    'अʃाँ': 'अम्माँ',      # mother
    'माकőट': 'मार्केट',    # market
    'ज़ŝरी': 'ज़रूरी',     # important
    'पũ': 'पत्र',         # letter
    'उʃीद': 'उम्मीद',     # hope
    'टŌेन': 'ट्रेन',       # train
    'िवʷास': 'विश्वास',    # confidence
    'उɎŐ': 'उन्हें',       # to them
    'खɄा': 'खन्ना',       # Khanna (name)
    'ख़ȏ': 'खत्म',        # finish
    'मœͤने': 'मैंने',       # I (ergative)
    'तुʉŐ': 'तुम्हें',     # to you
    'तुʉारा': 'तुम्हारा',   # your
    'तुʉारे': 'तुम्हारे',   # your (oblique)
    'तुʉारी': 'तुम्हारी',   # your (fem)
    'इʹ': 'इश्क़',        # romantic love
    'शमŊ': 'शर्म',        # shame
    'श˶': 'शख़्स',        # person
    'टŌक': 'ट्रक',        # truck
    'अİ̧': 'अक्सर',       # often
    'ȑोरी': 'भौंरी',       # brow (context dependent)
    'Ůधान': 'प्रधान',      # prime/main
    'मंũी': 'मंत्री',      # minister
    'ि˪ˋी': 'व्हिस्की',    # whisky
    'İखलौना': 'खिलौना',   # toy
    'बˑी': 'बस्ती',       # settlement
    'इ˓ी': 'इस्त्री',      # ironing
    'मरʃत': 'मरम्मत',     # repair
    'दुˑानी': 'दुस्तानी',   # -stani suffix

    # More conjunct fixes
    'Ȫ': 'द्र',           # dra
    'ț': 'ड़',            # hard da
    'Ț': 'ढ़',            # hard dha
    'Ż': 'ण्ड',           # nda (retroflex)
    'Ɵ': 'थ्',            # tha with halant

    # Additional fixes found in Unit 18
    'व˫': 'वक्त',         # time
    'टैƛी': 'टैक्सी',      # taxi
    'कŝँगी': 'करूँगी',     # I will do (fem)
    'कŝँगा': 'करूँगा',     # I will do (masc)
    'ŝँगी': 'रूँगी',       # -ruungi suffix
    'ŝँगा': 'रूँगा',       # -ruunga suffix
    'ŝप': 'रूप',          # form/beauty
    'ƛी': 'क्सी',         # ksi
    'ƛ': 'क्स',           # ks
    '˫': 'क्त',           # kta
    'ˋी': 'स्की',         # ski
    'ˋ': 'स्क',           # sk
    'Ȼर': 'क्तर',         # ktar
    'Ǝे': 'द्दे',          # dde
    'ǚ': 'ल्ल',           # lla
    'Ǜ': 'ल्ला',          # lla
    'ǜ': 'ल्लो',          # llo
    'Ƚ': 'ल्ह',           # lha
    'Ʉ': 'द्ध',           # ddha
    'ɉ': 'न्न',           # nna
    'Ɋ': 'न्ना',          # nna
    'ɬ': 'ल्क',           # lka
    'ɯ': 'म्ब',           # mba
    'ɰ': 'म्भ',           # mbha
    'ɶ': 'प्प',           # ppa
    'ɷ': 'प्पो',          # ppo
    'Ȟ': 'द्म',           # dma
    'Ƞ': 'द्न',           # dna
    'ȕ': 'द्व',           # dva
    'ȉ': 'द्दी',          # ddi
    'Ȉ': 'द्दा',          # dda
    'ȑ': 'द्दे',          # dde
    'ȶ': 'ळ',            # hard la
    'ɾ': 'रर',           # rra
    'ʉ': 'ह्म',           # hma
    'ʒ': 'ज़्',           # za with halant
    'ʔ': 'ह्',            # ha with halant
    'ʗ': 'क्क',           # kka
    'ʟ': 'ल्ल',           # lla
    'ʩ': 'श्च',           # shcha
    'ʭ': 'ह्व',           # hva
    'ʮ': 'ह्य',           # hya

    # More word-level fixes
    'िनकलŐगे': 'निकलेंगे',  # will come out
    'समझŐगे': 'समझेंगे',   # will understand
    'आइएगा': 'आइएगा',     # please come (formal)
    'Ůित': 'प्रति',        # per/towards
    'Ůतीत': 'प्रतीत',      # apparent
    'Ůिśद्ध': 'प्रसिद्ध',    # famous
    'Ůयोग': 'प्रयोग',      # use/experiment
    'Ůśन': 'प्रश्न',       # question
    'Ůभाव': 'प्रभाव',      # effect
    'Ůणाम': 'प्रणाम',      # greeting
    'ˢभाव': 'स्वभाव',      # nature/temperament
    'ˢयं': 'स्वयं',        # self
    'ˢीकार': 'स्वीकार',    # acceptance
    'ˢाद': 'स्वाद',        # taste
    'ˢागत': 'स्वागत',      # welcome
    '̾थान': 'स्थान',       # place
    '̾थित': 'स्थित',       # situated
    '̾थाई': 'स्थाई',       # permanent
    '̾थायी': 'स्थायी',      # permanent
    'İ̾थित': 'स्थिति',     # situation
    'पįर': 'परि',         # pari prefix
    'पįरवाįरक': 'पारिवारिक',  # familial
    'पįरवार': 'परिवार',    # family
    'पįर̾थित': 'परिस्थिति',  # circumstance
    'िवˑार': 'विस्तार',    # detail/expansion
    'िवʷिवद्यालय': 'विश्वविद्यालय',  # university
    'िवषय': 'विषय',       # subject/topic
    'िवदेश': 'विदेश',      # foreign
    'िवशेष': 'विशेष',      # special
    'िवभाग': 'विभाग',      # department
    'िनवेदन': 'निवेदन',    # request
    'िनबंध': 'निबंध',      # essay
    'िनयम': 'नियम',       # rule
    'िमलना': 'मिलना',      # to meet
    'िमठाई': 'मिठाई',      # sweets
    'िजससे': 'जिससे',      # from which
    'िजसके': 'जिसके',      # whose
    'िजसे': 'जिसे',        # whom
    'िजसकी': 'जिसकी',     # whose (fem)
    'िजसका': 'जिसका',     # whose (masc)
    'िजɎŐ': 'जिन्हें',      # whom (plural)
    'िबना': 'बिना',        # without
    'िबʝुल': 'बिल्कुल',    # absolutely
    'िदन': 'दिन',         # day
    'िदया': 'दिया',        # gave
    'िदए': 'दिए',         # gave (plural)
    'िदल': 'दिल',         # heart
    'िदʟी': 'दिल्ली',      # Delhi
    'िकताब': 'किताब',      # book
    'िकतना': 'कितना',      # how much
    'िकतने': 'कितने',      # how many
    'िकतनी': 'कितनी',     # how many (fem)
    'िकसी': 'किसी',       # someone
    'िकसे': 'किसे',        # whom
    'िकया': 'किया',        # did
    'िकए': 'किए',         # did (plural)
    'िलए': 'लिए',         # for/took
    'िलया': 'लिया',        # took
    'िलख': 'लिख',         # write
    'िसर': 'सिर',         # head
    'िसफ़Ŋ': 'सिर्फ़',       # only
    'िफर': 'फिर',         # again/then
    'िफ़ʝ': 'फ़िल्म',       # film
    'िफ़ʝी': 'फ़िल्मी',     # filmy
    'िहˑा': 'हिस्सा',      # part
    'िह̢दी': 'हिंदी',       # Hindi

    # IPA character fixes (verified against romanization)
    'ȯ': 'ध्य',           # dhya - e.g. ध्यान (dhyān)
    'ɨ': 'ब्द',           # bda - e.g. शब्दकोश (śabdkoś)
    'ɔ': 'प्प',           # ppa - e.g. चप्पल (cappal)
    'ɘ': 'प्ल',           # pla - e.g. प्लीज़ (plīz)
    'ɑ': 'ा',            # aa matra (might be standalone)
    'ɞ': 'द्य',           # dya

    # Word-level IPA fixes
    'अȯापक': 'अध्यापक',    # teacher
    'ȯान': 'ध्यान',        # attention
    'शɨकोश': 'शब्दकोश',    # dictionary
    'चɔल': 'चप्पल',        # sandal
    'ɘीज़': 'प्लीज़',       # please
    'िवद्यााथŎ': 'विद्यार्थी',  # student

    # More Latin Extended fixes (verified against romanization)
    'Ŏ': 'र्',            # ra with halant (in clusters)
    'ƃ': 'क्ट',           # kta - e.g. डाक्टर (ḍākṭar)
    'ǧ': 'ट्ठ',           # ttha - e.g. चिट्ठी (ciṭṭhī)
    'Ƒ': 'क्ल',           # kla - e.g. क्लास (klās)
    'ƶ': 'ग्य',           # gya - e.g. व्यंग्य (vyaṅgy)
    'Ɨ': 'क्ष',           # ksha
    'ǒ': 'ज्ञ',           # gya/jña
    'ƕ': 'ह्न',           # hna
    'Ƙ': 'क्क',           # kka
    'ƹ': 'ग्र',           # gra
    'ǥ': 'ट्ट',           # tta
    'ǭ': 'ऊ',            # long u vowel

    # Word-level Latin Extended fixes
    'कुसŎ': 'कुर्सी',       # chair (kursī)
    'कुसŎयाँ': 'कुर्सियाँ',   # chairs
    'डाƃर': 'डाक्टर',      # doctor (ḍākṭar)
    'डॉƃर': 'डॉक्टर',      # doctor
    'िचǧी': 'चिट्ठी',       # letter (ciṭṭhī)
    'िचिǧयाँ': 'चिट्ठियाँ',   # letters
    'Ƒास': 'क्लास',        # class (klās)
    'गमŎ': 'गर्मी',        # heat (garmī)
    'श्चंƶ': 'व्यंग्य',      # sarcasm
    'बफ़Ŏ': 'बर्फ़ी',       # barfi (sweet)

    # More Latin Extended fixes (round 2)
    'ŵ': 'श्र',           # śra - e.g. श्री (śrī)
    'ŷ': 'स्र',           # sra
    'Ÿ': 'ह्र',           # hra
    'ſ': 'क्क',           # kka - e.g. इक्कीस (ikkīs)
    'ƀ': 'क्ख',           # kkha - e.g. मक्खी (makkhī)
    'ƅ': 'क्ति',          # kti - e.g. व्यक्ति (vyakti)
    'Ţ': 'क्र',           # kra - e.g. क्रिकेट (krikeṭ)
    'ť': 'त्य',           # tya
    'Ű': 'द्ध',           # ddha
    'ű': 'द्धा',          # ddha

    # Word-level fixes (round 2)
    'ŵी': 'श्री',          # Mr/Lord (śrī)
    'ŵीमती': 'श्रीमती',    # Mrs (śrīmatī)
    'इſीस': 'इक्कीस',      # 21
    'शुŢवार': 'शुक्रवार',   # Friday
    'िŢकेट': 'क्रिकेट',    # cricket
    'मƀी': 'मक्खी',        # fly
    'मखिƀयाँ': 'मक्खियाँ',  # flies
    'मƀन': 'मक्खन',        # butter
    'पſे': 'पक्के',        # ripe
    'पſा': 'पक्का',        # ripe (masc)
    'श्चखिƅ': 'व्यक्ति',    # person

    # Standalone character fixes (not in word context)
    'Š': 'हु',            # hu - e.g. बहुत (bahut)
    'š': 'हू',            # hū (long)
    'ŝ': 'रू',            # rū - e.g. ज़रूर (zarūr)
    'Ō': 'ड्र',           # ḍra
    'ō': 'ट्र',           # ṭra
    'ĩ': 'ी',            # long i matra
    'į': 'ि',            # short i matra

    # More word-level fixes
    'ज़ŝर': 'ज़रूर',        # certainly (zarūr)
    'बŠत': 'बहुत',         # very (bahut)
    'बš': 'बहू',          # daughter-in-law (bahū)
    'ŝसी': 'रूसी',        # Russian
    'सुल्हर': 'सुन्दर',     # beautiful (sundar)
    'टŌ': 'ट्र',          # ṭra
    'डŌ': 'ड्र',          # ḍra
    'Ů': 'प्र',           # pra (standalone)

    # More word fixes (round 3)
    'िसफ़र्म': 'सिर्फ़',      # only (sirf)
    'सिर्मफ़': 'सिर्फ़',      # only (sirf) - alternate corruption
    'खिखड़की': 'खिड़की',    # window (khiṛkī)
    'खिड़खी': 'खिड़की',     # window
    'अलमािरयाँ': 'अलमारियाँ',  # cupboards
    'अलमाįरयाँ': 'अलमारियाँ',  # cupboards (alternate)
    'कुरिसयाँ': 'कुर्सियाँ',   # chairs
    'हैी': 'हैं',           # are (corrupted ending)
    'सिर्मफ़': 'सिर्फ़',      # only (sirf) - exact from file
    'खिखड़की': 'खिड़की',    # window - exact from file

    # Fixes from validation report (round 4)
    'मूितर्म': 'मूर्ति',      # statue (mūrti)
    'पद्दार': 'पत्थर',       # stone (patthar)
    'उदूर्म': 'उर्दू',        # Urdu (urdū)
    'माचर्म': 'मार्च',        # March (mārc)

    # Fixes from validation report (chapters 5, 10, 15)
    'माकőट': 'मार्केट',      # market (mārkeṭ)
    'ह˹ा': 'हफ़्ता',         # week (haftā)
    'तर˯ी': 'तरक़्क़ी',       # progress (taraqqī)
    'Űा˦ण': 'ब्राह्मण',      # Brahmin (brāhmaṇ)
    'शİƅ': 'शक्ति',         # power (śakti)
    'सɶी': 'सब्ज़ी',         # vegetables (sabzī)
    'उपɊास': 'उपन्यास',      # novel (upanyās)
    'बोįरयत': 'बोरियत',      # boredom
    '˘ान': 'स्नान',          # bath (snān)
    'जʗी': 'जल्दी',          # quickly (jaldī)
    '˹': 'फ़्त',            # fta
    '˯': 'क़्क़',            # qqe
    '˦': 'ह्म',             # hma
    '˘': 'स्न',             # sna
}

# Regex patterns for systematic fixes
REGEX_FIXES = [
    # Fix standalone matra issues
    (r'मŐ', 'में'),        # men (in)
    (r'हŐ', 'हें'),        # hen
    (r'लŐ', 'लें'),        # len
    (r'करŐ', 'करें'),      # karen
    (r'बोलŐ', 'बोलें'),    # bolen
    (r'आएŐ', 'आएं'),      # aayen
    (r'जाएŐ', 'जाएं'),    # jaayen

    # Fix i-matra at word start (should follow consonant, not precede)
    # Pattern: standalone ि at start of word followed by consonant
    (r'\bिज़द', 'ज़िद'),    # obstinacy
    (r'\bिक\b', 'कि'),     # that (conjunction)
    (r'\bिपता', 'पिता'),   # father
    (r'\bदुिनया', 'दुनिया'),  # world
    (r'\bलेिकन', 'लेकिन'),  # but
    (r'\bिनकल', 'निकल'),   # come out
    (r'\bिमल', 'मिल'),     # meet
    (r'कहािनयों', 'कहानियों'),  # stories
    (r'ज़ािहर', 'ज़ाहिर'),   # evident
]


def fix_text(text: str) -> str:
    """Apply all character fixes to text."""
    # Apply direct character mappings (longest first to avoid partial matches)
    for corrupted, correct in sorted(CHAR_MAP.items(), key=lambda x: -len(x[0])):
        text = text.replace(corrupted, correct)

    # Apply regex fixes
    for pattern, replacement in REGEX_FIXES:
        text = re.sub(pattern, replacement, text)

    return text


def analyze_remaining_issues(text: str) -> set:
    """Find remaining non-standard characters that might need fixing."""
    # Standard Devanagari range: U+0900–U+097F
    # Standard Latin + common punctuation
    issues = set()
    for char in text:
        code = ord(char)
        # Skip standard ranges
        if code < 128:  # ASCII
            continue
        if 0x0900 <= code <= 0x097F:  # Devanagari
            continue
        if 0x0980 <= code <= 0x09FF:  # Bengali (shouldn't be here)
            issues.add((char, hex(code), 'Bengali?'))
        elif 0x00C0 <= code <= 0x024F:  # Latin Extended
            issues.add((char, hex(code), 'Latin Extended'))
        elif 0x0250 <= code <= 0x02AF:  # IPA Extensions
            issues.add((char, hex(code), 'IPA'))
        elif 0x1E00 <= code <= 0x1EFF:  # Latin Extended Additional
            issues.add((char, hex(code), 'Latin Ext Add'))
        elif code > 0x02FF:  # Other weird chars
            issues.add((char, hex(code), 'Other'))
    return issues


def process_file(filepath: Path, dry_run: bool = False) -> tuple[int, set]:
    """Process a single markdown file. Returns (changes_made, remaining_issues)."""
    with open(filepath, 'r', encoding='utf-8') as f:
        original = f.read()

    fixed = fix_text(original)
    changes = sum(1 for a, b in zip(original, fixed) if a != b)

    issues = analyze_remaining_issues(fixed)

    if not dry_run and fixed != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(fixed)

    return changes, issues


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Fix Devanagari encoding in extracted textbook')
    parser.add_argument('--dry-run', action='store_true', help='Analyze without modifying files')
    parser.add_argument('--path', default='textbook', help='Path to markdown files')
    args = parser.parse_args()

    # Support both relative and absolute paths
    if args.path.startswith('/'):
        textbook_dir = Path(args.path)
    else:
        # Default: look in study-materials/textbook relative to repo root
        textbook_dir = Path(__file__).parent.parent / 'study-materials' / 'textbook'
        if args.path != 'textbook':
            textbook_dir = Path(__file__).parent / args.path
    if not textbook_dir.exists():
        print(f"Directory not found: {textbook_dir}")
        return

    all_issues = set()
    total_changes = 0

    for md_file in sorted(textbook_dir.glob('*.md')):
        changes, issues = process_file(md_file, dry_run=args.dry_run)
        total_changes += changes
        all_issues.update(issues)

        status = "would fix" if args.dry_run else "fixed"
        if changes > 0:
            print(f"{md_file.name}: {status} ~{changes} characters")

    print(f"\nTotal: ~{total_changes} character changes")

    if all_issues:
        print(f"\nRemaining non-standard characters ({len(all_issues)}):")
        for char, code, category in sorted(all_issues, key=lambda x: x[1]):
            print(f"  '{char}' {code} ({category})")
        print("\nAdd these to CHAR_MAP if they represent corrupted Devanagari.")


if __name__ == '__main__':
    main()
