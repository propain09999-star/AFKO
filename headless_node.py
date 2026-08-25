import grpc
from concurrent import futures
import time
import chameleon_network_pb2
import chameleon_network_pb2_grpc

class HeadlessChameleonWorker(chameleon_network_pb2_grpc.ChameleonNodeManagerServicer):
    def AlignQuantumVector(self, request, context):
        print(f"[NETWORK INGEST] Received state N={request.master_state_n} from master loop.")
        
        # Parse runtime environment values to adapt internal processing
        if request.current_temperature >= 70:
            print("[ALERT] Node thermals high. Triggering conservative recovery mode.")
            status = chameleon_network_pb2.CoherenceResponse.RECOVERING
            # Execute conservative modification math
            mutated_n = (request.master_state_n * 6) // 25
        else:
            status = chameleon_network_pb2.CoherenceResponse.COHERENT
            # Execute aggressive modification math
            mutated_n = (request.master_state_n * 324) // 5

        # Ensure state mutations stay safely within boundary targets
        if mutated_n == 0:
            mutated_n = 1 # Force reset to protect baseline arithmetic loop

        return chameleon_network_pb2.CoherenceResponse(
            status=status,
            mutated_state_n=mutated_n,
            tracking_log="Arithmetic transformation processed successfully at O(1)."
        )

def serve_headless_instance(port):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
    chameleon_network_pb2_grpc.add_ChameleonNodeManagerServicer_to_server(
        HeadlessChameleonWorker(), server
    )
    server.add_insecure_port(f'[::]:{port}')
    print(f"[INSTANCE STARTED] Headless node listening actively on port {port}...")
    server.start()
    server.wait_for_termination()

if __name__ == '__main__':
    # Start worker locally on designated port interface
    serve_headless_instance(port=50051)
