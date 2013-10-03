import uuid
import json
import time
import subprocess
import libvirt
import random
import os

def createVM(imagePath,name,ram,cpu,arch,targetMachine):

    # got machine, create xml, copy vmImage to machine, define VM
    mac = [random.randint(0x00, 0x7f), random.randint(0x00, 0xff), random.randint(0x00, 0xff) ]
    macID =  ':'.join(map(lambda x: "%02x" % x, mac))

    target = {}

    target['name'] = name
    target['uuid'] = str(uuid.uuid4())
    target['memm'] = str(int(ram)*1024)
    target['emul'] = '/usr/bin/qemu-system-i386' if int(arch) == 32 else '/usr/bin/qemu-system-x86_64'
    target['vcpu'] = int(cpu)
    target['arch'] = 'x86_64' if int(arch) == 64 else 'i686'
    target['path'] = imagePath
    target['macc'] = macID


    #######################
    # CreateXML
    xml = open('../src/actual_ref.xml', 'r').read()
    xml = xml % (target['name'], target['uuid'], target['memm'], target['memm'], target['vcpu'], target['arch'], target['emul'], target['path'], target['macc'])
    print xml
    #qemu+ssh://user@host/system
    connDest = "qemu+ssh://"+targetMachine+"/system"
    conn = libvirt.open(connDest)
    try:
    	conn.defineXML(xml)
    	vm = conn.lookupByName(name)
    	vm.create()
    	returnID = vm.ID()
    	conn.close()
    	return returnID
    except Exception, e:
   	print e
	return -1

def destroyVM(targetMachine,vmid):
    connDest = "qemu+ssh://"+targetMachine+"/system"
    conn = libvirt.open(connDest)
    try:
    	vm=conn.lookupByID(vmid)
	vm.destroy()
	vm.undefine()
	return 0
    except Exception, e:
   	print e
	return -1
