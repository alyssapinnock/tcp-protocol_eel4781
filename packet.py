"""
Name: Alyssa Pinnock
Course: EEL 4781 - Computer Communication Networks
Project: Programming Project - Option C (TCP-Like Protocol)
Description: Packet Class: creates a packet/segment that will be sent
"""


class Packet:
    def __init__(self, seqNum, isAck=False, ackNum=-1, data=None, checksum=0):
        self.seqNum = seqNum    # seq number
        self.isAck = isAck        # True if ACK, False if Data
        self.ackNum = ackNum      # ACK number (used for cumul. ACKs)
        self.data = data       
        self.checksum = checksum 

    def __repr__(self):
        if self.isAck:
            return f"[ACK: {self.ackNum}]"
        else:
            return f"[DATA: {self.seqNum}]"