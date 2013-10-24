import subprocess
import uuid
import json
import time
import libvirt
import random
import col
import sys
import os
import rados
import rbd


confPath = '/etc/ceph/ceph.conf'
poolName = 'rbd'

# create the vm
def createVM(imagePath,name,ram,cpu,arch,targetMachine,imageBit):

    # got machine, create xml, copy vmImage to machine, define VM
    mac = [random.randint(0x00, 0x7f), random.randint(0x00, 0xff), random.randint(0x00, 0xff) ];
    macID =  ':'.join(map(lambda x: "%02x" % x, mac));

    target = {};

    target['name'] = name;
    target['uuid'] = str(uuid.uuid4());
    target['memm'] = str(int(ram)*1024);
    target['emul'] = '/usr/bin/qemu-system-i386' if int(arch) == 32 else '/usr/bin/qemu-system-x86_64';
#    target['emul'] = '/usr/bin/kvm';
    target['vcpu'] = int(cpu);
    target['arch'] = 'x86_64' if int(imageBit) == 64 else 'i686';
    target['path'] = imagePath;
    target['macc'] = macID;

    #######################
    # CreateXML

    xml = open('../src/actual_ref.xml', 'r').read();
    xml = xml % (target['name'], target['uuid'], target['memm'], target['memm'], target['vcpu'], target['arch'], target['emul'], target['path'], target['macc']);
    print xml;
    #######################
    #qemu+ssh://user@host/system
    connDest = "qemu+ssh://"+targetMachine+"/system";
    conn = libvirt.open(connDest);
    try:
    	conn.defineXML(xml);
    	vm = conn.lookupByName(name);
    	vm.create();
    	returnID = vm.ID();
    	conn.close();
    	return returnID;
    except Exception, e:
   	print e;
	return -1;

def destroyVM(targetMachine,vmid):
	connDest = "qemu+ssh://"+targetMachine+"/system";
    	conn = libvirt.open(connDest);
    	try:
		#check for volumes attached to it and detach them
		vm=conn.lookupByID(vmid);
		vm.destroy();
		vm.undefine();	
    		conn.close();
		return 0;
	except Exception, e:
   		print e;
		return -1;


def createVolume(volName,volSize):
	# createVolume
	volName = volName.encode('ascii', 'ignore')
        volSize = volSize*(1024**3)
	print volSize,volName;
	with rados.Rados(conffile = confPath) as cluster:
 		with cluster.open_ioctx(poolName) as ioctx:
            		rbd_inst = rbd.RBD()
            		try:
                		rbd_inst.create(ioctx, volName, volSize)
    			except Exception, e:
   				print e;
                		return -1
	return 0;


def destroyVolume(volumeDetails):
	# destroyVolume
	volName=volumeDetails[2].encode('ascii','ignore');
	with rados.Rados(conffile = confPath) as cluster:
        	with cluster.open_ioctx(poolName) as ioctx:
			rbd_inst = rbd.RBD();
			try:
				rbd_inst.remove(ioctx, volName);
				return 0;
    			except Exception, e:
   				print e;
				return -1;
	return -1;


def attachVolume(targetMachine,volumeDetails,vmid,count):

    	xml = open('../src/storage.xml').read();
	volName=volumeDetails[2].encode('ascii','ignore');
    	volURL = 'rbd/' + volName;
	monList=[];
	monID=None;
	port=6789;

	conffile = open(confPath).read().split('\n')
        for i in conffile:
            if 'mon_initial_members' in i:
                monList = i.split('=')[1].strip();
                monID = monList.split(',')[0].strip();
	
    	xml = xml%(volURL, monID, 'hd' + str(chr(ord('a')+count)))
	
	print xml

    	connDest = "qemu+ssh://"+targetMachine+"/system";
    	conn = libvirt.open(connDest);
    	try:
		#attachVolume
    		domain = conn.lookupByID(vmid)
    		domain.attachDevice(xml)
    		conn.close();
		return xml;
    	except Exception, e:
   		print e;
		return -1;


def detachVolume(targetMachine,volumeDetails,vmid):
	xml=volumeDetails[5];
    	connDest = "qemu+ssh://"+targetMachine+"/system";
    	conn = libvirt.open(connDest);
    	try:
		#detachVolume
		domain = conn.lookupByID(vmid)
		domain.detachDevice(xml)
    		conn.close();
		return 0;
    	except Exception, e:
   		print e;
		return -1;

