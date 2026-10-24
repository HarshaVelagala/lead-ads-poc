import { Platform } from "react-native";

const defaultHost = Platform.OS === "android" ? "10.0.2.2" : "localhost";
const configuredUrl = process.env.EXPO_PUBLIC_API_URL;

export const API_URL = (configuredUrl || `http://${defaultHost}:8000`).replace(/\/$/, "");
export const WS_URL = API_URL.replace(/^http/, "ws") + "/ws/leads";