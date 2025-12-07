"""
Name: Alyssa Pinnock
Course: EEL 4781 - Computer Communication Networks
Project: Programming Project - Option C (TCP-Like Protocol)
Description: Network channel simulator that handles propagation delay 
and the logic for manually dropping packets (loss).
"""

class Channel:
    def __init__(self, loss_data, loss_ack, delay=1, log_callback=None):
        # list to keep track of packets currently traveling.
        # format: [packet, ticks_remaining, destination, total_delay]
        self.in_transit = []         
        self.loss_data = loss_data   # list of seq numbers to drop
        self.loss_ack = loss_ack     # list of ack numbers to drop
        self.delay = delay           
        self.log = log_callback      # function to write to the UI log

    def send_to_channel(self, packet, destination_obj):
        # first, check if this DATA packet is supposed to be lost based on config
        if not packet.isAck and packet.seqNum in self.loss_data:
            msg = f"DROP DATA {packet.seqNum} (Config)"
            print(f"   >>> [CHANNEL] {msg}")
            if self.log: self.log(msg, color=(255, 0, 0)) 
            
            # important: i have to remove this from the list. 
            # if i don't, the retransmission will just get dropped again and loop forever.
            self.loss_data.remove(packet.seqNum) 
            return 
            
        # next, check if this ACK packet is supposed to be lost
        if packet.isAck and packet.ackNum in self.loss_ack:
            msg = f"DROP ACK {packet.ackNum} (Config)"
            print(f"   >>> [CHANNEL] {msg}")
            if self.log: self.log(msg, color=(255, 0, 0)) 
            
            # same logic here, remove it so the next ack gets through
            self.loss_ack.remove(packet.ackNum)
            return 

        # if it wasn't dropped, add it to the transit list with the delay
        self.in_transit.append([packet, self.delay, destination_obj, self.delay])

    def tick(self):
        # this moves time forward. decrease delay for everything in transit.
        arrived = []
        for item in self.in_transit:
            item[1] -= 1
            if item[1] <= 0:
                arrived.append(item)
        
        # keep only the stuff that hasn't arrived yet
        self.in_transit = [x for x in self.in_transit if x[1] > 0]
        
        # deliver the arrived packets to their destination (sender or receiver)
        for packet, _, destination, _ in arrived:
            destination.receive(packet)

    def kill_specific_packet(self, target_packet):
        # this helper is used by the UI when i click a packet to delete it manually
        for i, item in enumerate(self.in_transit):
            if item[0] == target_packet:
                self.in_transit.pop(i)
                return True
        return False