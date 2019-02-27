#data files are numbered on the server.
#for exmaple imuRaw1.mat, imuRaw2.mat and so on.
#write a function that takes in an input number (1 through 6)
#reads in the corresponding imu Data, and estimates
#roll pitch and yaw using an extended kalman filter

from matplotlib import pyplot as plt
import scipy.io as sio
import numpy as np
import itertools
import math
import Quaternion
import ukf
import warnings
import timeit

# def findAccelerometerSensitivity(ax,ay,az):
# 	return  np.sqrt(ax*ax+ay*ay+az*az)/(9.8*1023)
#
# def findBias(x, y, z, scalefactor, results):
# 	bias = np.zeros((3,))
# 	bias[0] = (x*scalefactor - results[0])/scalefactor
# 	bias[1] = (y*scalefactor - results[1])/scalefactor
# 	bias[2] = (z*scalefactor - results[2])/scalefactor
# 	return bias
# Check for singular
def rottoeuler(r):
	norm = np.sqrt(r[2,1]**2 + r[2,2]**2)
	roll_x = np.arctan(r[2,1]/r[2,2])
	pitch_y = np.arctan(-r[2,0]/norm)
	yaw_z = np.arctan(r[1,0]/r[0,0])
	return roll_x, pitch_y, yaw_z

def rottoeuler2(r):
	norm = np.sqrt(r[2,1]**2 + r[2,2]**2)
        roll_x = np.arctan2(r[2,1],r[2,2])
        pitch_y = np.arctan2(-r[2,0],norm)
        yaw_z = np.arctan2(r[1,0],r[0,0])
        return roll_x, pitch_y, yaw_z

def estimate_rot(data_num=1):
	#your code goes here
	imu_raw = sio.loadmat('imu/imuRaw'+str(data_num)+'.mat')
	imu_vals = imu_raw['vals']
	imu_ts = imu_raw['ts'].T
	imu = imu_vals#[:,:-100]
	#vicon_raw = sio.loadmat('vicon/viconRot'+str(data_num)+'.mat')
	#vicon_rot = vicon_raw['rots']
	#vicon_ts = vicon_raw['ts'].T
	#vicon = vicon_rot[:,:,16:]
	#vicon = vicon[:,:,16:]
	#imu = imu[:,:vicon.shape[2]]
	ax = -1*imu[0,:]
	ay = -1*imu[1,:]
	az = imu[2,:]
	acc = np.array([ax, ay, az]).T
	wx = imu[4,:]
	wy = imu[5,:]
	wz = imu[3,:]
	omega = np.array([wx, wy, wz]).T
	scale_acc = 3300/1023/330.0
	bias_acc = np.mean(acc[:50], axis = 0) - (np.array([0,0,1])/scale_acc)
	if data_num == 3:
		bias_acc = np.mean(acc[:1], axis = 0) - (np.array([0,0,1])/scale_acc)
	acc = (acc-bias_acc)*scale_acc
	scale_omega = 3300/1023/3.33
	bias_omega = np.mean(omega[:500], axis = 0)
	if data_num==3:
		bias_omega = np.mean(omega[:250], axis = 0)
	omega = (omega-bias_omega)*scale_omega*(np.pi/180)
	#vicon_rolls = np.zeros((vicon.shape[2],))
	#vicon_pitches = np.zeros((vicon.shape[2],))
	#vicon_yaws = np.zeros((vicon.shape[2],))
	#for i in range(vicon.shape[2]):
	#	vicon_rolls[i], vicon_pitches[i], vicon_yaws[i] = rottoeuler(vicon[:,:,i])
	previous_state_x = np.array([1,0,0,0])
	P = 2*np.eye(3,3)
	Q = 8*np.eye(3,3)
	R = 8*np.eye(3,3)
	if data_num == 3:
		Q = 50*np.eye(3,3)
	
        	Q[1,2] = 100
		R = 250*np.eye(3,3)
	# print(bias_acc)
	predictions = np.zeros((3,3,ax.shape[0]))
	#start = timeit.default_timer()
	for i in range(ax.shape[0]):
		omegai = omega[i]
		W = ukf.sigma_points(P,Q)
		X = ukf.WtoX(W, previous_state_x)
		#if i==ax.shape[0]-1:
		Y = ukf.XtoY(X,0.01, omegai)
		#else:
		#Y = ukf.XtoY(X,imu_ts[i+1]-imu_ts[i], omegai)
		# print(Y)
		ymean, W = ukf.meanY(Y, previous_state_x)
		#print(ymean)
		pk = ukf.calculatepk(W)
		Z = ukf.YtoZ(Y)
		zmean  = np.mean(Z, axis = 0)
		zmean = zmean/np.linalg.norm(zmean)
		v = ukf.innovation(zmean, acc[i])
		pzz = ukf.pzz(Z, zmean)
		pvv = ukf.pvv(pzz, R)
		pxz = ukf.pxz(W, Z, zmean)
		kk = ukf.kalman_gain(pxz, pvv)

		previous_state_x = ukf.update_state(pk,kk,v,ymean)
		P = ukf.update_cov(pk, kk, pvv)
		predictions[:,:,i] = Quaternion.quattorot(previous_state_x)
	#stop = timeit.default_timer()
	#print("Time: ",stop-start)
	prediction_rolls = np.zeros((predictions.shape[2],))
	prediction_pitches = np.zeros((predictions.shape[2],))
	prediction_yaws = np.zeros((predictions.shape[2],))
        if data_num <=4:
		for i in range(predictions.shape[2]):
			prediction_rolls[i], prediction_pitches[i], prediction_yaws[i] = rottoeuler(predictions[:,:,i])
	else:
        	for i in range(predictions.shape[2]):
                        prediction_rolls[i], prediction_pitches[i], prediction_yaws[i] = rottoeuler2(predictions[:,:,i])

	#print(prediction_rolls)
	#print(prediction_pitches)
	#print(prediction_yaws)
	
        if data_num == 3:
                prediction_pitches[-650:] = 0
		prediction_yaws[-650:] = 0	
	return prediction_rolls, prediction_pitches, prediction_yaws
	#roll_diff = (prediction_rolls-vicon_rolls)**2
	#yaws_diff = (prediction_yaws - vicon_yaws)**2
	#pitch_diff = (prediction_pitches - vicon_pitches)**2
	#print(np.sqrt(yaws_diff.mean()))
	#total = (roll_diff+yaws_diff+pitch_diff).mean()
	#print(np.sqrt(total))
#	plt.plot(prediction_rolls)
#	plt.plot(vicon_rolls)
#	plt.show()
#	plt.plot(prediction_pitches)
#	plt.plot(vicon_pitches)
#	plt.show()
#	plt.plot(prediction_yaws)
#	plt.plot(vicon_yaws)
#	plt.show()

#if __name__ == "__main__":

#	estimate_rot(data_num=5)
