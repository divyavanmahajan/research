import Foundation

enum RemoteKey: String, CaseIterable {
    case power       = "KEY_POWER"
    case volumeUp    = "KEY_VOLUMEUP"
    case volumeDown  = "KEY_VOLUMEDOWN"
    case mute        = "KEY_MUTE"
    case channelUp   = "KEY_CHUP"
    case channelDown = "KEY_CHDOWN"
    case up          = "KEY_UP"
    case down        = "KEY_DOWN"
    case left        = "KEY_LEFT"
    case right       = "KEY_RIGHT"
    case ok          = "KEY_ENTER"
    case back        = "KEY_RETURN"
    case home        = "KEY_HOME"
    case menu        = "KEY_MENU"

    var smartThingsCommand: String {
        switch self {
        case .volumeUp:    return "volumeUp"
        case .volumeDown:  return "volumeDown"
        case .mute:        return "mute"
        case .channelUp:   return "channelUp"
        case .channelDown: return "channelDown"
        case .power:       return "setSwitch"
        default:           return "sendKey"
        }
    }

    var smartThingsArguments: [AnyHashable] {
        switch self {
        case .power: return ["off"]
        default:     return [rawValue]
        }
    }
}
