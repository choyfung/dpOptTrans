import numpy as np
from scipy.linalg import inv
import os.path, re
import subprocess as subp
from js.geometry.quaternion import Quaternion
import argparse, sys
from helpers import *

def EvalError(q_gt, t_gt, q, t):
  if q is None or t is None:
    return np.nan, np.nan
  print "gt  rotation:    ", q_gt.q
  print "est rotation:    ", q.q
  print "gt  translation: ", t_gt
  print "est translation: ", t
  err_a = q_gt.angleTo(q)*180./np.pi
  err_t = np.sqrt(((t_gt-t)**2).sum())
  return err_a, err_t

def DisplayPcs(scanApath, scanBpath, q,t, plotCosies, stopToDisplay,
    displayNormals):
  from js.data.plyParse import PlyParse
  from js.utils.plot.colors import colorScheme
  from js.geometry.rotations import plotCosy
  import mayavi.mlab as mlab
  colors = colorScheme("label")
  print "parsing", scanApath
  plyA = PlyParse();
  plyA.parse(scanApath)
  pcA = plyA.getPc()
  nA = plyA.getNormals()
  print "parsing", scanBpath
  plyB = PlyParse();
  plyB.parse(scanBpath)
  pcB = plyB.getPc()
  nB = plyB.getNormals()

  R = q.toRot().R

  figm = mlab.figure(bgcolor=(1,1,1))
  mlab.points3d(pcA[:,0], pcA[:,1], pcA[:,2], mode="point",
      color=colors[0])
#  if plotCosies:
#    plotCosy(figm, np.eye(3), np.zeros(3), 0.5)
#    plotCosy(figm, R.T, -R.T.dot(t), 0.5)

  R = R.T
  t = -R.dot(t)
  pcB = (1.001*R.dot(pcB.T)).T + t
  nB = (1.001*R.dot(nB.T)).T

  mlab.points3d(pcB[:,0], pcB[:,1], pcB[:,2], mode="point",
        color=colors[1])

  if displayNormals:
    figm = mlab.figure(bgcolor=(1,1,1))
    mlab.points3d(nA[:,0], nA[:,1], nA[:,2], mode="point",
        color=colors[0])
    mlab.points3d(nB[:,0], nB[:,1], nB[:,2], mode="point",
          color=colors[1])

  if stopToDisplay:
    mlab.show(stop=True)

#cfgNYU = {"name":"nyu", "lambdaS3": [30., 45.,60., 75, 90.], "lambdaR3": 1.}
cfgNYU = {"name":"nyu", "lambdaS3": [45.], "lambdaR3": 0.5}
cfgNYU = {"name":"nyu", "lambdaS3": [45., 65, 80], "lambdaR3": 0.5}
cfgNYU = {"name":"nyu", "lambdaS3": [45., 65, 80], "lambdaR3": 0.1}
cfgNYU = {"name":"nyu", "lambdaS3": [45., 65, 80], "lambdaR3": 0.2,
    "maxLvlR3":15, "maxLvlS3":15}

cfg = cfgNYU

showUntransformed = False
useSurfaceNormalsInICP = True

parser = argparse.ArgumentParser(description = 'randomly sample two renders and align them')
parser.add_argument('-i','--input',
    default="../data/middle.ply", \
    help='path to input pointcloud .ply file or to a config file pointing to existing ply files s')
parser.add_argument('-o','--output',
    default="./", \
    help='path to output .json results file')
parser.add_argument('-p','--prefix',
    default="out", \
    help='prefix for temp files')
parser.add_argument('-a','--angle', default=30., help='magnitude of random angle')
parser.add_argument('-t','--translation', default=1., help='magnitude of random translation')
parser.add_argument('-m','--minOverlap', default=70., help='min overlap between sampled point clouds')
parser.add_argument('-d','--display', action="store_true",
    help='display aligned point clouds')
cmdArgs = parser.parse_args()

resultsPath = cmdArgs.output + "/" + os.path.splitext(os.path.split(cmdArgs.input)[1])[0]
outputPath = "/scratch/optRotTrans/" + cmdArgs.prefix
nameA = cmdArgs.prefix+"_A"
nameB = cmdArgs.prefix+"_B"
transformationPathBB = '{}_{}_BB.csv'.format(nameA, nameB)
transformationPathBBICP = '{}_{}_BB_ICP.csv'.format(nameA, nameB)
transformationPathBBEGI = '{}_{}_BBEGI.csv'.format(nameA, nameB)
transformationPathBBEGIICP = '{}_{}_BBEGI_ICP.csv'.format(nameA, nameB)
transformationPathICP = '{}_{}_ICP.csv'.format(nameA, nameB)
transformationPathEGI = '{}_{}_EGI.csv'.format(nameA, nameB)
transformationPathMM = '{}_{}_MM.csv'.format(nameA, nameB)
transformationPathMMICP = '{}_{}_MM_ICP.csv'.format(nameA, nameB)
transformationPathFFT = '{}_{}_FFT.csv'.format(nameA, nameB)
transformationPathFFTICP = '{}_{}_FFT_ICP.csv'.format(nameA, nameB)
transformationPathGoICP = '{}_{}_GoICP.csv'.format(nameA, nameB)
transformationPathGogma = '{}_{}_Gogma.csv'.format(nameA, nameB)

paramEvalLambdaS3 = [45., 60., 80 ] #, 90.]
paramEvalLambdaR3 = [0.5, 0.75, 1.0]

paramEvalLambdaS3 = [45. ] #, 90.]
paramEvalLambdaR3 = [0.5]

tryMfAmbig = False
cfg["maxLvlS3"] = 11
#cfg["maxLvlR3"] = 11

runMM = False
runMMICP = False
runBBEGI = False
runBBEGIICP = False
runBBeval = False
runFFT    =False
runFFTICP =False
runICP    =False
runBB     =False
runBBICP  =False
runGoICP  =False
runGogma  =False
runMap    =False
runMapICP =False

#runFFT    =True
#runFFTICP =True
#runICP    =True
#runBB     =True
#runBBICP  =True
#runGoICP  =True
#runGogma  =True
#runMap    =True
#runMapICP =True

#runFFT    =True
#runGoICP =True
#runGogma  =True
#runMap    =True
runBB =True
#runBBICP =True

showOnLargeDeviation =True
err_a_thr = 2.
err_t_thr = 0.3

version = "1.4" # large scale eval of all algos and RunBB
version = "1.5" # eval of BB vor different parameters
version = "1.51" # eval of more different BB parameters as well as the best of approach
version = "2.0" # squashed fabs bug
version = "2.1" # more targeted eval to get more samples.
version = "2.2" # made BB for translation more stable.
version = "2.3" # more fine tuning of BB
version = "2.4" # moment matching
version = "2.5" # actual sampling of point clouds.
version = "2.6" # fixed sampling of point clouds. Gigantic eval - currently in final version of paper.
version = "2.7" # implementing and testing multi cluster tracking...
version = "2.8" # evaluating multi rotation cluster optimization
version = "2.9" # only temporary for GoICP
version = "2.91" # GoICP with trim=0.2 
version = "2.92" # GoICP with trim=0.2 and timeout at 10min
version = "2.93" # trying to improve translation accuracy for BB (lambdaT smaller; eps smaller in BB)
version = "3.0" # simple rotation
version = "3.01" # back to simple rotation from two clusters; improved ICP
version = "3.02" # fixed a bunch of stuff but mainly the sampling of scenes
version = "3.03" # going back to BB in rotation and translation
version = "3.04" # more fine grained lambdaT
version = "3.05" # early termination of rotations to get multiple peaks (lvl 8)
version = "3.06" # early termination of rotations to get multiple peaks (lvl 11)
version = "3.07" # eval on 3Dsim data
 
validInput = False
if re.search("config_[0-9]+.txt", cmdArgs.input):
  with open(cmdArgs.input) as f:
    scanApath = os.path.join(os.path.split(cmdArgs.input)[0],f.readline()[:-1])
    scanBpath = os.path.join(os.path.split(cmdArgs.input)[0],f.readline()[:-1])
    f.readline()
    x = np.loadtxt(f)
    # T_gt is T_ba but the saved config is T_ab
    q_gt = Quaternion(w=x[3],x=x[0],y=x[1],z=x[2]).inverse()
    t_gt = -q_gt.rotate(x[4:7])
    data_gt = x[7:]

  paramString = os.path.splitext(os.path.split(cmdArgs.input)[1])[0]
  print paramString

  q_A = Quaternion(1,0,0,0)
  t_A = np.array([0,0,0])
  q_B = Quaternion(1,0,0,0)
  t_B = np.array([0,0,0])

  if os.path.isfile(scanApath) and os.path.isfile(scanBpath):
    validInput = True
  else:
    validInput = False
else:
  args = ['../build/bin/renderPcFromPc',
      '-i ' + cmdArgs.input,
      '-o ' + outputPath,
      '-a {}'.format(cmdArgs.angle), 
      '-t {}'.format(cmdArgs.translation), 
      '-m {}'.format(cmdArgs.minOverlap), 
      ]
  print " ".join(args)
  validInput = (subp.call(" ".join(args), shell=True) == 0)

  paramString = 'angle_{}_translation_{}'.format(int(cmdArgs.angle),
      int(cmdArgs.translation))
  scanApath = outputPath+"_A_"+paramString+".ply"
  scanBpath = outputPath+"_B_"+paramString+".ply"
  # load gt
  gtPath = outputPath+"_"+paramString+"_TrueTransformation.csv"
  scanAtruePath = outputPath+"_"+paramString+"_Transformation_A_W.csv"
  scanBtruePath = outputPath+"_"+paramString+"_Transformation_B_W.csv"
  q_gt, t_gt, data_gt = LoadTransformationAndData(gtPath)
  q_A, t_A, data_A = LoadTransformationAndData(scanAtruePath)
  q_B, t_B, data_B = LoadTransformationAndData(scanBtruePath)

if validInput:
  R_A = q_A.toRot().R
  R_B = q_B.toRot().R
  R_BA = R_B.dot(R_A.T)
  t_BA = -R_BA.dot(t_A) + t_B

  results = {"GT":{"q":q_gt.q.tolist(), "t":t_gt.tolist(),
    "q_A_W":q_A.q.tolist(), "t_A_W":t_A.tolist(),
    "q_B_W":q_B.q.tolist(), "t_B_W":t_B.tolist(),
    "overlap":data_gt[0], "sizeA":data_gt[1], "sizeB": data_gt[2],
    # compute magnitude of translation as well as rotation of the two
    # viewpoints of the scene. 
    "dtranslation": np.sqrt((t_BA**2).sum()),
    "dangle": q_A.angleTo(q_B)*180./np.pi
    },
    "version":version}

  if showUntransformed:
    q0 = Quaternion(1.,0.,0.,0.)
    DisplayPcs(scanApath, scanBpath, q0, np.zeros(3), False, False)
    DisplayPcs(scanApath, scanBpath, q_gt,t_gt, True, True)

  if runGogma:
    q,t,dt,success = RunGogma(scanApath, scanBpath, transformationPathGogma)
    if not success:
      err_a, err_t = np.nan, np.nan
    else:
      err_a, err_t = EvalError(q_gt, t_gt, q, t)
    print "Gogma: {} deg {} m".format(err_a, err_t)
    results["Gogma"] = {"err_a":err_a, "err_t":err_t, "q":q.q.tolist(),
        "t":t.tolist(), "dt":dt}

  if runGoICP:
    q,t,dt,success = RunGoICP(scanApath, scanBpath, transformationPathGoICP)
    if not success:
      err_a, err_t = np.nan, np.nan
    else:
      err_a, err_t = EvalError(q_gt, t_gt, q, t)
    print "GoICP: {} deg {} m".format(err_a, err_t)
    results["GoICP"] = {"err_a":err_a, "err_t":err_t, "q":q.q.tolist(),
        "t":t.tolist(), "dt":dt}

  if runFFT:
    q,t,dt,success = RunFFT(scanApath, scanBpath, transformationPathFFT)
    if not success:
      err_a, err_t = np.nan, np.nan
      runFFTICP = False
    else:
      err_a, err_t = EvalError(q_gt, t_gt, q, t)
    print "FFT: {} deg {} m".format(err_a, err_t)
    results["FFT"] = {"err_a":err_a, "err_t":err_t, "q":q.q.tolist(),
        "t":t.tolist(), "dt":dt}
    # write chosen transformation back to file for ICP
    if runFFTICP:
      with open(transformationPathFFT,'w') as f: 
        f.write("qw qx qy qz tx ty tz\n")
        f.write("{} {} {} {} {} {} {}\n".format(
          q.q[0],q.q[1],q.q[2],q.q[3],t[0],t[1],t[2]))

  if runFFTICP:
    q,t,dt2,success = RunICP(scanApath, scanBpath, transformationPathFFTICP,
        useSurfaceNormalsInICP, transformationPathFFT)
    if not success:
      err_a, err_t = np.nan, np.nan
    else:
      err_a, err_t = EvalError(q_gt, t_gt, q, t)
    print "FFT+ICP: {} deg {} m".format(err_a, err_t)
    results["FFT+ICP"] = {"err_a":err_a, "err_t":err_t,
        "q":q.q.tolist(), "t":t.tolist(), "dt":dt+dt2}

  if runMap:
    q,t,Ks, dt,success = RunBB(cfg, scanApath, scanBpath,
        transformationPathBB, simpleTranslation=False,
        simpleRotation=True, tryMfAmbig=True)
    if not success:
      err_a, err_t = np.nan, np.nan
      if np.isnan(t).all(): # only translation is messed up -> err_a
        err_a, _ = EvalError(q_gt, t_gt, q, t)
      runBBICP = False
    else:
      err_a, err_t = EvalError(q_gt, t_gt, q, t)
    print "Map: {} deg {} m".format(err_a, err_t)
    results["Map"] = {"err_a":err_a, "err_t":err_t, "q":q.q.tolist(),
        "t":t.tolist(), "Ks":Ks.tolist(), "dt":dt}

  if runMapICP:
    q,t,dt2,success = RunICP(scanApath, scanBpath, transformationPathBBICP,
        useSurfaceNormalsInICP, transformationPathBB)
    if not success:
      err_a, err_t = np.nan, np.nan
    else:
      err_a, err_t = EvalError(q_gt, t_gt, q, t)
    print "Map+ICP: {} deg {} m".format(err_a, err_t)
    results["Map+ICP"] = {"err_a":err_a, "err_t":err_t,
        "q":q.q.tolist(), "t":t.tolist(), "dt":dt+dt2}

  if runBB:
    q,t,Ks, dt,success = RunBB(cfg, scanApath, scanBpath,
        transformationPathBB, simpleTranslation=False,
        tryMfAmbig=tryMfAmbig)
    if not success:
      err_a, err_t = np.nan, np.nan
      if np.isnan(t).all(): # only translation is messed up -> err_a
        err_a, _ = EvalError(q_gt, t_gt, q, t)
      runBBICP = False
    else:
      err_a, err_t = EvalError(q_gt, t_gt, q, t)
    print "BB: {} deg {} m".format(err_a, err_t)
    results["BB"] = {"err_a":err_a, "err_t":err_t, "q":q.q.tolist(),
        "t":t.tolist(), "Ks":Ks.tolist(), "dt":dt}
    
  if cmdArgs.display or (showOnLargeDeviation and \
      (err_a > err_a_thr or err_t > err_t_thr)):
    DisplayPcs(scanApath, scanBpath, q,t, True, True, False)

  if runBBICP:
    q,t,dt2,success = RunICP(scanApath, scanBpath, transformationPathBBICP,
        useSurfaceNormalsInICP, transformationPathBB)
    if not success:
      err_a, err_t = np.nan, np.nan
    else:
      err_a, err_t = EvalError(q_gt, t_gt, q, t)
    print "BB+ICP: {} deg {} m".format(err_a, err_t)
    results["BB+ICP"] = {"err_a":err_a, "err_t":err_t,
        "q":q.q.tolist(), "t":t.tolist(), "dt":dt+dt2}

  if cmdArgs.display or (showOnLargeDeviation and \
      (err_a > err_a_thr or err_t > err_t_thr)):
    DisplayPcs(scanApath, scanBpath, q,t, True, True, False)

  if runBBEGI:
    q,t,Ks,dt,success = RunBB(cfg, scanApath, scanBpath,transformationPathBBEGI,True)
    if not success:
      err_a, err_t = np.nan, np.nan
      if np.isnan(t).all(): # only translation is messed up -> err_a
        err_a, _ = EvalError(q_gt, t_gt, q, t)
      runBBEGIICP = False
    else:
      err_a, err_t = EvalError(q_gt, t_gt, q, t)
    print "BBEGI: {} deg {} m".format(err_a, err_t)
    results["BBEGI"] = {"err_a":err_a, "err_t":err_t, "q":q.q.tolist(),
        "t":t.tolist(), "Ks":Ks.tolist(), "dt":dt}

  if runBBEGIICP:
    q,t,dt2,success = RunICP(scanApath, scanBpath, transformationPathBBEGIICP,
        useSurfaceNormalsInICP, transformationPathBBEGI)
    if not success:
      err_a, err_t = np.nan, np.nan
    else:
      err_a, err_t = EvalError(q_gt, t_gt, q, t)
    print "BBEGI+ICP: {} deg {} m".format(err_a, err_t)
    results["BBEGI+ICP"] = {"err_a":err_a, "err_t":err_t,
        "q":q.q.tolist(), "t":t.tolist(), "dt":dt+dt2}


#    q0 = Quaternion(1.,0.,0.,0.)
#    DisplayPcs(scanApath, scanBpath, q0, np.zeros(3), False, False, False)
#    DisplayPcs(scanApath, scanBpath, q,t, False,False,False)
##    print "displaying"
#    DisplayPcs(scanApath, scanBpath, q.inverse(),-q.toRot().R.T.dot(t),
#        True,True,False)


  if runBBeval:
    for lambdaS3 in paramEvalLambdaS3:
      for lambdaR3 in paramEvalLambdaR3:
        q,t,Ks,dt,success = RunBBsimple(scanApath, scanBpath,
            transformationPathBB, lambdaS3, lambdaR3)
        if not success:
          print "BB simple failed - hopefully due to mutliple maxima."
          raw_input()
          err_a, err_t = np.nan, np.nan
          if np.isnan(t).all(): 
            # only translation is messed up -> err_a
            err_a, _ = EvalError(q_gt, t_gt, q, t)
          runBBICPsimple = False
        else:
          err_a, err_t = EvalError(q_gt, t_gt, q, t)
        key = "BB_{}_{}".format(lambdaS3, lambdaR3)
        print key+": {} deg {} m".format(err_a, err_t)
        results[key] = {"err_a":err_a, "err_t":err_t,
            "q":q.q.tolist(), "t":t.tolist(), "Ks":Ks.tolist(),
            "dt":dt, "lambdaS3":lambdaS3, "lambdaR3":lambdaR3}

  if runMM:
    q,t,dt,success = RunMM(scanApath, scanBpath, transformationPathMM)
    if not success:
      err_a, err_t = np.nan, np.nan
      runMMICP = False
    else:
      err_a, err_t = EvalError(q_gt, t_gt, q, t)
    print "MM: {} deg {} m".format(err_a, err_t)
    results["MM"] = {"err_a":err_a, "err_t":err_t, "q":q.q.tolist(),
        "t":t.tolist(), "dt":dt}

  if runMMICP:
    q,t,dt2,success = RunICP(scanApath, scanBpath, transformationPathMMICP,
        useSurfaceNormalsInICP, transformationPathMM)
    if not success:
      err_a, err_t = np.nan, np.nan
    else:
      err_a, err_t = EvalError(q_gt, t_gt, q, t)
    print "MM+ICP: {} deg {} m".format(err_a, err_t)
    results["MM+ICP"] = {"err_a":err_a, "err_t":err_t,
        "q":q.q.tolist(), "t":t.tolist(), "dt":dt+dt2}

  if runICP:
    q,t,dt,success = RunICP(scanApath, scanBpath, transformationPathICP,
        useSurfaceNormalsInICP)
    if not success:
      err_a, err_t = np.nan, np.nan
    else:
      err_a, err_t = EvalError(q_gt, t_gt, q, t)
    print "ICP: {} deg {} m".format(err_a, err_t)
    results["ICP"] = {"err_a":err_a, "err_t":err_t, "q":q.q.tolist(),
        "t":t.tolist(), "dt":dt}

  if cmdArgs.display:
    DisplayPcs(scanApath, scanBpath, q,t, True, True, False)

  import json, time
#  print results
#  import ipdb
#  ipdb.set_trace()
  stamp = "{}".format(int(np.floor(time.time()*1e3)))
  json.dump(results, open(resultsPath+"_"+stamp+'_results.json','w'))
  print "done"

  sys.exit(0)
sys.exit(1)
