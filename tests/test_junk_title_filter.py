"""Regression tests for the tightened junk-title filter.

Background: syllabus-policy prose ("Summative = 75%"), OneNote note fragments
("Which type of bond creates full charges on atoms..."), and lesson-text
sentences ("In order for theorems to be properly applied, we need...") were
becoming calendar events. `_JUNK_TITLE_RE` alone could not catch them, so both
`scrapers.assignment_calendar._is_junk_title` (the calendar gate) and
`scrapers.canvas_page_extractor._clean_task_title` (the source) gained a
shared `_prose_title_reject` layer. These tests pin its behavior.

The two module copies must stay in sync: the gate mirrors the extractor so
feeds that bypass the extractor (Notion, Google Docs, cached rows from older
runs) are filtered identically. ``test_gate_and_extractor_stay_in_sync``
enforces that.
"""

from __future__ import annotations

import pytest

from scrapers.assignment_calendar import _is_junk_title
from scrapers.canvas_page_extractor import _clean_task_title

# Rows observed as real calendar events in the live store (2026-09-10 audit):
# syllabus policy, OneNote note pages, lesson text, survey questions, and
# mangled table fragments. None are actionable tasks.
SYLLABUS_PROSE = [
    "Summative = 75%",
    "Formative = 25%",
    "(midterm and final exam multiplier = 1)",
    "* The above resources are web-based",
    "It is the expectation of Forsyth County Schools that",
    "Students are eligible for one summative reassessment",
    "AP teachers utilize AP Classroom, the Bluebook digital",
    "AP® English Language and Composition Course and Exam Description",
    "* College Readiness Math (CLEP Exam)",
    "* EOC Courses (EOC Exam)",
    "take an external end-of-course exam as a part of the",
    "* All formative work must be completed and turned in.",
    "* Formative Assessments include, but are not limited",
    "Final Exam Exemption: Students may exempt the final",
]
NOTE_FRAGMENTS = [
    "The Nucleus",
    "Which type of bond creates full charges on atoms after the bond forms?",
    "Main ideas / Questions for class:",
    "Guiding questions:",
    "Resource 1: Belier's notes about control groups and hypotheses",
    "Notes for 2.1 - SA / V ratio and cell size",
    "4. pH 9 is times more acidic than pH 8.",
    "Cell membrane = plasma membrane",
    "Organelles with their own membrane, so for structure describe what they look like and how they",
    "Fungi absorb food after digesting it outside their bodies",
    "First major division in cell type: prokaryote vs. eukaryote",
    "Limit laws, left and right hand limits, limits at infinity",
]
LESSON_TEXT = [
    "In order for theorems to be properly applied, we need to meet the certain conditions.",
    "In this lesson, we will explore our first existence theorem.",
    "Continuity of a function will prove to be an important characteristic in many theorems for our",
    "An object dropped from a state of rest at time t = 0 travels a distance s = 4.9 meters in t sec",
    "How far does the object travel during the time interval (2.5, 3)?",
    "Find the average velocity of the object over [2.5, 3].",
    "i(0) is undefined",
    "i(4) = 5",
]
SURVEY_AND_MISC = [
    "What is your favorite school subject?",
    "How do you feel about starting AP Statistics?",
    "Name you go by if different:",
    "Phonetic Spelling of Name:",
    "CONTACT FOR STUDENTS/APPLICANTS",
    "Completes BioBuilder project and presents at",
    "Ideal for anyone with heavy Fall commitments (ie: Band, Theatre, Fall Sport) or anyone new to s",
    "As you submit your completed Officer applications, you will be called for interviews. You need",
    "Many of you have the starting date prior to 10/20 but",
    "in a grocery bag, every bag of candy must be visible",
    "\"I got to hear perspectives I never would have",
    "Chocolate dipped for an additional 50 cents",
    "The total cost of the cone",
]

MUST_REJECT = SYLLABUS_PROSE + NOTE_FRAGMENTS + LESSON_TEXT + SURVEY_AND_MISC

# Real tasks observed in the live store; none may ever be rejected.
MUST_KEEP = [
    "Review for AP Exam",
    "Unit 1 Quiz 1",
    "LOR Quiz",
    "Chapter 4 Reading Quiz",  # opener-shaped word + task keyword
    "Enzyme lab final draft (1 per group)",
    "1SP - Which Word First",
    "Freshmen Officer Application",
    "Unit 1A Test (1.1 - 1.6)",
    "Midpoint formative quiz (covers OneNote lessons 1.2 - 1.5)",
    "1.2 Homework",  # section number, not a numbered-list fragment
    "Student Council Application",  # "students" opener must not fire bare
    "Read pages 41-45 of unit packet",  # lowercase action-verb start
    "Infinite Limits and Limits at Infinity Homework",  # "X = Y" math task
    "AP Statistics FRQ Test Sampling Experiments 2026 A",
    "Unit 3: Collecting Data (Chapters 4.1 - 4.3)",
    "Standard Error of the Mean (SEM)",
    "Reading: Chapter 4: A tour of the cell",
    "Macromolecule structures and functions from textbook",
    "Enzyme activity and substrate specificity",
    "ch3 protein folding",
    "Diffusion and Osmosis Lab Activities",
    "Write a proposal for the 2025 iGEM continuation",
    "Complete lab safety quiz and Google form signature sheet with parents by Thursday 8/13",
    "Study Guide Quiz Unit 1: Safety and Industry",
    "SFHS Over and Under",
    "Cells and transport (unit 2) midpoint quiz (deadline: 9/25)",
    "AP Classroom (Unit 1A Progress Check) due 8/24 @ 8:00",
    "Fri. 9/11 | SOAPStone Quiz! You will not have to write",
    "Unit 1A Program Set due 8/24 @ 8:00 AM",
    "The Lab Report Draft",  # short "The X" heading that names work
    "Membrane structure group review",
    "WA2a",
    "U2Q2",
]


@pytest.mark.parametrize("title", MUST_REJECT, ids=lambda t: t[:40])
def test_prose_rows_are_rejected(title):
    assert _is_junk_title(title), f"junk leaked through the gate: {title!r}"


@pytest.mark.parametrize("title", MUST_KEEP, ids=lambda t: t[:40])
def test_real_tasks_survive_the_gate(title):
    assert not _is_junk_title(title), f"false positive at the gate: {title!r}"


@pytest.mark.parametrize("title", MUST_REJECT, ids=lambda t: t[:40])
def test_extractor_drops_prose_rows(title):
    assert _clean_task_title(title) == "", f"junk survived the extractor: {title!r}"


@pytest.mark.parametrize("title", MUST_KEEP, ids=lambda t: t[:40])
def test_extractor_keeps_real_tasks(title):
    assert _clean_task_title(title) != "", f"false positive in extractor: {title!r}"


def test_gate_and_extractor_stay_in_sync():
    """The gate and extractor must agree on every pinned title.

    The extractor returns "" for junk; the gate returns True. The two module
    copies of the prose filter are mirrored by hand (a back-import would be
    circular), so this test is the tripwire against drift.
    """
    for title in MUST_REJECT + MUST_KEEP:
        assert _is_junk_title(title) == (_clean_task_title(title) == ""), (
            f"gate/extractor disagree on {title!r}"
        )
