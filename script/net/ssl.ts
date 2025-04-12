
import { Config, setGlobalProperties } from "../config.js"
import { RPCMsgType } from "../message.js"
import { unwrapArgs } from "../utils/utils.js"
import { ssl_st_structOf, SSL3_RANDOM_SIZE } from "./struct.js"
import { FileHelper, help, NativePointerObject } from "../helper.js"
import { Libssl } from "../lib/libssl.js"
import { FuncHelper } from "../func.js"


type SSL3_STATE = {
    read_sequence: ArrayBuffer
    cwrite_sequence: ArrayBuffer
    server_random: ArrayBuffer
    client_random: ArrayBuffer
}


interface SSLField {
    method: NativePointer
    config: NativePointer
    version: number
    max_send_fragment: number
    rbio: NativePointer
    wbio: NativePointer
    do_handshake: NativePointer
    s3: SSL3_STATE
    d1: NativePointer
    msg_callback: NativePointer
    msg_callback_arg: NativePointer
    initial_timeout_duration_ms: number
    session: NativePointer
    info_callback: NativePointer
    ctx: NativePointer
    session_ctx: NativePointer
    ex_data: NativePointer
}


interface SSL extends SSLField { }

const HEX_TABLE = '0123456789abcdef'



export type SSLSecretLog = {
    label: string
    client_random: string
    secret: string
}

class SSL extends NativePointerObject {
    constructor(handle: NativePointer) {
        super(handle)
        for (let [field, offseter] of Object.entries(Process.pointerSize === 8 ? ssl_st_structOf.B64 : {})) {
            Object.defineProperty(this, field, {
                value: offseter(this.$handle),
                writable: false,
                enumerable: true,
            })
        }
    }


    static cbb_hex(bytes: ArrayBuffer, in_len: number): string {
        const bs = new Uint8Array(bytes)
        const hex_list: string[] = []
        for (let i = 0; i < in_len; i++) {
            hex_list.push(HEX_TABLE[bs[i] >> 4] + HEX_TABLE[bs[i] & 0xf])
        }
        return hex_list.join('')
    }

    secretlog(label: string, secret: ArrayBuffer, secret_len: number): SSLSecretLog {
        return {
            label,
            client_random: SSL.cbb_hex(this.s3.client_random, SSL3_RANDOM_SIZE),
            secret: SSL.cbb_hex(secret, secret_len),
        }
    }

}



function sendSSLSecret(tag: string, data: { label: string, client_random: string, secret: string }){
    if (Config.OnRPC) {
        help.$send({
            type: RPCMsgType.SSL_SECRET,
            data: {
                tag: tag,
                ...data
            }
        })
    } else {
        const file = help.getLogfile(tag, 'a')
        file.writeLine(`${data.label} ${data.client_random} ${data.secret}`)
        file.flush()
    }
}


class SSLTools extends NativePointerObject {
    private static _libssl_hook: boolean = false

    static newConsumer(tag: string): SSLSecretCallbackConsumer {
        return new SSLSecretCallbackConsumer(tag)
    }

    static attachLogSecret(tag: string = 'sslkey.log'){
        if (this._libssl_hook) {
            return true
        }
        const handle = Libssl.SSL_new.$handle
        if (!handle || handle.isNull()) {
            return false
        }
        this._libssl_hook = true
        Interceptor.attach(handle,{
            onEnter(args) {
                const [ctx] = unwrapArgs(args, 1)
                this.ssl_ctx = ctx
            },
            onLeave(retval){
                const ctx = this.ssl_ctx
                Libssl.SSL_CTX_set_keylog_callback(ctx, FuncHelper.SSL_CTX_keylog_callback(
                    Libssl.SSL_CTX_get_keylog_callback(ctx), 
                    (impl: NativeFunction<NativePointer, Array<NativePointer>>, ssl: NativePointer, line: NativePointer) => {
                        const str = line.readCString()
                        if (str !== null) {
                            const sep_list = str.split(' ')
                            if(sep_list.length !== 3) {
                                printErr(`[attachLogSecret] error to parse secret_log[${str}]`)
                            }else{
                                const [label, client_random, secret] = sep_list
                                sendSSLSecret(tag, { label, client_random, secret })
                            }
                        }
                        if(!impl.isNull()) {
                            impl(ssl, line)
                        }
                    }
                ))
            }
        })
        return true
    }


}


export class SSLSecretCallbackConsumer {
    private tag: string

    constructor(tag: string) {
        this.tag = tag
    }

    Handler(): ScriptInvocationListenerCallbacks {
        const that = this
        return {
            onEnter(args: InvocationArguments): void {
                const [ssl, label, secret, secret_len] = unwrapArgs(args, 4)
                const handle = new SSL(ssl)
                const len = secret_len.toUInt32()
                const data = handle.secretlog(label.readCString(), secret.readByteArray(len), len)
                sendSSLSecret(that.tag, data)
            },
            onLeave(retval: InvocationReturnValue): void {

            }
        }
    }

}


export { SSLTools }





setGlobalProperties({
    'SSLTools': SSLTools,
})