#!/usr/bin/env python3
# Author: jim.carroll@docker.com  (of original version for python2.7)
# converted to python3 with the help of 2to3 application by gdoumas,
# and expanded to output the OS version, hypervisor (and show a more modern output with MCR,MKE,MSR instead of ENGINE,UCP,DTR)
# Purpose: To overcome the limitations of the shell-based version of `sd_nodes`
# Tested On (by gdoumas@mirantis.com Georgios Doumas) for Python 3.8.5  in Ubuntu20.04 as a LinuxSubsystem4Windows
# Requirements: The script is run from inside the folder containing the extracted support dump, especially : ucp-nodes.txt

import json
import os
import fnmatch
from operator import itemgetter
from functools import reduce

ucp_nodes = 'ucp-nodes.txt'

def findfile(topdir, f_glob):
    for d_name, sd_name, f_list in os.walk(topdir):
        for f_name in f_list:
            if fnmatch.fnmatch(f_name, f_glob):
                return os.path.join(d_name, f_name)


def getddcver(nodename,f_glob,k):
    f = findfile(nodename,f_glob)
    if f == None:
        return '-'
    else:
        with open(f, 'r') as r:
            j = json.load(r)

        env = j[0]['Config']['Env']
        # print env
        imgverstr = [s for s in env if k in s]
        # print imgverstr[0]
        imgver = imgverstr[0].split('=')[1]
        return imgver


def row_print(r, w):
    print('{:{w0}}  {:{w1}}  {:{w2}}  {:{w3}}  {:{w4}}  {:{w5}}  {:{w6}}  {:{w7}}  {:{w8}}  {:{w9}}  {:{w10}}  {:{w11}}  {:{w12}}  {:{w13}}  {:{w14}}'.format(
            *r, w0=w[0], w1=w[1], w2=w[2], w3=w[3], w4=w[4], w5=w[5], w6=w[6], w7=w[7], w8=w[8], w9=w[9], w10=w[10], w11=w[11], w12=w[12], w13=w[13], w14=w[14])  )


def full_os_details(hostname):
    node_dsinfo_filename = os.path.join(hostname, "dsinfo", "dsinfo.txt")
    os_type = "-"
    os_version = "---"
    dsi_os = " NoInfo "   ## docker system info result
    full_os_text = os_type + '-' + os_version + '/' + dsi_os
    hpv = " None "
    try:      ## after setting some default values, we see what the dsinfo.txt file has
        with open(node_dsinfo_filename, 'r') as inf:
            for line in inf:
                line = line.lstrip()
                if line.startswith("Operating System: "):
                    dsi_os = line.split(': ')[1].strip()
                    dsi_os = dsi_os.replace('Red ', 'R').replace('Hat ', 'H').replace('Enterprise ', 'E')
                    dsi_os = dsi_os.split('(')[0]  # RHEL 7.9 (Maipo) will become RHEL 7.9
                if line.startswith("NAME="):
                    os_type = line.split('=')[1].strip().strip('"')
                    ## Just to make the output a little shorter
                    if os_type.startswith("Red"):
                        os_type = "RHEL"
                if line.startswith("VERSION="):
                    os_version = line.split('=')[1].strip().strip('"')
                    os_version = os_version.split('(')[0]   ## 20.04.1 LTS (Focal Fossa)  --> 20.04.1 LTS
                full_os_text = os_type + '-' + os_version + '/' + dsi_os
              
                if line.startswith("Hypervisor vendor: "):
                    hpv = line.split(': ')[1].strip()
                    break
                if line.startswith("mount"):   # reached this point? you will not find any line about Hypervisor, stop reading the rest of the file
                    break
            full_os_text = os_type + '-' + os_version + '/' + dsi_os
            return full_os_text, hpv  #in case that the dsinfo.txt file has no line starting with Hypervisor vendor:  at least return - as hpv
    except FileNotFoundError:        # for nodes that the SD did not gather info, at least return the default values
        return full_os_text, hpv


def getnodes(f):
    node_tuples = []

    with open(f, 'r') as r:
        sd = json.load(r)

    for node in sd:
        hostname = 'N/A'
        if 'Hostname' in node['Description']:
            hostname = node['Description']['Hostname']

        id = node['ID'][:10]

        if node['Spec']['Role'] == 'manager':
            if 'Leader' in node['ManagerStatus'] and node['ManagerStatus']['Leader'] == True:
                role = 'leader'
            else:
                role = 'manager'
        else:
            role = 'worker'

        arch = "N/A"
        os = "N/A"
        os_string = "N/A"
        addr = "N/A"
        hypervisor = '-'
        if 'Architecture' in node['Description']['Platform']:
            arch = node['Description']['Platform']['Architecture']
        if 'OS' in node['Description']['Platform']:
            os = node['Description']['Platform']['OS']
            if os == "linux":
                os_string, hypervisor = full_os_details(hostname)
        avail = node['Spec']['Availability']
        state = node['Status']['State']
        if 'Addr' in node['Status']:
            addr = node['Status']['Addr']

        if addr == '127.0.0.1' or addr == '0.0.0.0':
            addr = node['ManagerStatus']['Addr']

        addr = addr.replace(':2377','')
        engver = "N/A"
        if 'EngineVersion' in node['Description']['Engine']:
            engver = node['Description']['Engine']['EngineVersion']
        collect = node['Spec']['Labels']['com.docker.ucp.access.label']

        o_swarm = o_kube = '-'
        if 'com.docker.ucp.orchestrator.swarm' in node['Spec']['Labels'] and node['Spec']['Labels']['com.docker.ucp.orchestrator.swarm'] == 'true':
            o_swarm = 'swarm'
        if 'com.docker.ucp.orchestrator.kubernetes' in node['Spec']['Labels'] and node['Spec']['Labels']['com.docker.ucp.orchestrator.kubernetes'] == 'true':
            o_kube = 'kube'
        orch = '/'.join([o_swarm, o_kube])

        stsmsg = "N/A"
        if 'Message' in node['Status']:
            stsmsg = node['Status']['Message']

        ucpver = getddcver(hostname,'ucp-proxy.txt','IMAGE_VERSION')
        dtrver = getddcver(hostname,'dtr-registry-*.txt','DTR_VERSION')
        if dtrver != '-':
            role += '/MSR'
        ucpdtrver = '/'.join([ucpver,dtrver])

        c_at = node['CreatedAt'].split('T')[0]
        u_at = node['UpdatedAt'].split('T')[0]
        t_stamps = '/'.join([c_at,u_at])

        node_tuples.append((hostname, id, role, os, os_string, hypervisor, avail, state, addr, engver, ucpdtrver, collect, orch, t_stamps, stsmsg))

    s = sorted(node_tuples, key=itemgetter(2,0))
    w = []
    for i in range(len(node_tuples[0])):
        w.append(len(max(s, key = lambda x: len(x[i]))[i]))

    header = 'HOSTNAME ID ROLE OS OS_VERSION/docker_info_os HpVs AVAIL STATE IP MCR MKE/MSR COLLECT ORCHESTR CREATED/UPDATED STATUS_MESSAGE'
    row_print(header.split(' '), w)
    linemax = reduce(lambda x, y: x+y, w) + (2 * (len(w) - 1))
    print('-' * linemax)
    for row in s:
        row_print(row, w)


if __name__ == "__main__":
    getnodes(ucp_nodes)
