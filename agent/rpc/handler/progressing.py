
from agent.rpc.resolver import RPC
from agent.rpc.message import RPCMsgType, RPCPayload
from agent.logger import LoggerName, get_logger



@RPC.on_message(RPCMsgType.PROGRESSING)
def on_progressing(payload: RPCPayload):
    data = payload.message.data
    if data.error:
        print(f"[x] | {data.tag} | {data.step} => {data.error}", file=get_logger(LoggerName.stderr))
    else:
        print(f"[~] | {data.tag} | {data.step} => {data.extra.get('intro', ','.join(list(data.extra.keys())))}", 
              file=get_logger(LoggerName.stdout))