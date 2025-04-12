



export function setGlobalProperties(keyValues: { [key: string]: any }): void {
    for (let [k, v] of Object.entries(keyValues)) {
        if (k in global) {
            throw new Error(`global property[${k}] exists already`)
        }
        (global as any)[k] = v
    }
}



export const enum LogLevel {
    DEBUG = 0,
    INFO = 1,
    WARN = 2,
    ERROR = 3,


    _MUST_LOG = 9999999,
}



declare global {
    const enum LogLevel {
        DEBUG = 0,
        INFO = 1,
        WARN = 2,
        ERROR = 3,
    }

}

export class Config {
    static OnRPC: boolean = false
    static OutputDir?: string
    static LogLevel: number = LogLevel.INFO
    static LogCollapse: boolean = true
}



setGlobalProperties({
    'Config': Config,
})

