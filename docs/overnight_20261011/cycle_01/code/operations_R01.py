"""Exact modelling functions extracted from the saved R01 checkpoint recipe.
Source mesh and reflection map remain local; see MANIFEST.json.
No new engine or scheduler.
"""
import numpy as np

def gauss(t,c,w):return np.exp(-((t-c)/w)**2)

def smooth(a,b,x):t=np.clip((x-a)/(b-a),0,1);return t*t*(3-2*t)

def sculpt(v,key,revision):
    w=v.copy();x,y,z=v.T
    window=smooth(.70,1.60,z)*(1-smooth(8.70,10.40,z))
    # Fixed hand-authored section pivots follow the existing support. No
    # bounding-box fitting, global depth squeeze or new material phase field.
    cx=-4.30+.30*gauss(z,6.20,2.70)
    cy=.20*gauss(z,9.0,2.0)
    if key=='D_TORQUE':
        angle=(.78*gauss(z,3.40,1.70)-.90*gauss(z,7.00,1.65)+.40*gauss(z,9.10,.85))*window
        sx=1-.12*gauss(z,5.30,.75)+.08*gauss(z,7.40,.80)
        sy=1-.10*gauss(z,5.30,.80)
        offset=np.zeros(len(v))
    elif key=='D_KNUCKLE':
        angle=(.50*gauss(z,3.00,1.40)-.95*gauss(z,6.70,1.15)+.65*gauss(z,8.90,.70))*window
        sx=1-.20*gauss(z,3.90,.70)+.28*gauss(z,5.50,1.00)-.18*gauss(z,7.40,.60)
        sy=1-.16*gauss(z,3.90,.80)+.15*gauss(z,5.50,.90)-.20*gauss(z,7.40,.65)
        offset=.55*gauss(z,5.90,.90)-.35*gauss(z,8.40,.70)
    else:
        angle=(.70*gauss(z,3.50,1.70)-.65*gauss(z,7.10,1.70))*window
        sx=1+.18*gauss(z,8.80,.90)-.12*gauss(z,6.80,.90)
        sy=1-.15*gauss(z,8.80,.90)
        offset=.40*gauss(z,8.80,1.10)
    # Same finite rotation as the preserved RETURN shoulder edit, oriented
    # in XY here. Each horizontal support section keeps all existing folds.
    u=(x-cx)*sx;vlocal=(y-cy)*sy
    w[:,0]=cx+u*np.cos(angle)-vlocal*np.sin(angle)
    w[:,1]=cy+u*np.sin(angle)+vlocal*np.cos(angle)+offset
    if key=='D_CONFLUX':
        # Existing finite return operation used over the attached arch, not
        # new stacked capitals. Reflection makes the two flows correspond.
        x,y,z=w.T
        turn=.42*gauss(np.abs(x),2.15,1.70)*smooth(9.30,12.0,z)
        dy=y-.10;dz=z-11.40
        w[:,1]=.10+dy*np.cos(turn)-dz*np.sin(turn)
        w[:,2]=11.40+dy*np.sin(turn)+dz*np.cos(turn)
        w[:,1]+=.70*gauss(x,0,1.80)*smooth(10.50,12.40,z)
    return w,dict(additional_horizontal_section_rotation=angle,
                  section_width_scale=sx,section_depth_scale=sy,section_depth_offset=offset)
