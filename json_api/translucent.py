# conda install mayavi
# pip install pysurfer
# export QT_API=pyqt
from surfer import Brain
import time
import os


if not os.environ.get("SUBJECTS_DIR"):
	os.environ["SUBJECTS_DIR"] = '/Applications/freesurfer/subjects'
if not os.environ.get("QT_API"):
	os.environ["QT_API"] = 'pyqt'
if not os.environ.get("LOCAL_DIR"):
	os.environ["LOCAL_DIR"] = '/Applications/freesurfer/local'
if not os.environ.get("FMRI_ANALYSIS_DIR"):
	os.environ["FMRI_ANALYSIS_DIR"] = '/Applications/freesurfer/fsfast'

subject_id = "fsaverage"

brain = Brain(subject_id, "both", "pial", cortex='ivory', alpha=0.5)

coords = [[-20, 10, 10], [-25, 22, 15], [-18, 8, 20]]
brain.add_foci(coords, color="red", hemi="lh")



print("GOING TO SLEEP")

raw_input()
