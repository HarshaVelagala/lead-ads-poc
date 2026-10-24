import React from "react";
import { StyleSheet, Text, View } from "react-native";

interface ConnectionStateProps {
  connected: boolean;
  message?: string;
}

export default function ConnectionState({ connected, message }: ConnectionStateProps) {
  return (
    <View style={[styles.container, connected ? styles.online : styles.offline]}>
      <View style={[styles.dot, connected ? styles.onlineDot : styles.offlineDot]} />
      <Text style={styles.text}>
        {message || (connected ? "Live connection" : "Connecting to backend...")}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    alignSelf: "flex-start",
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 16,
    marginTop: 10,
  },
  online: { backgroundColor: "#E8F5EE" },
  offline: { backgroundColor: "#FFF1E8" },
  dot: { width: 7, height: 7, borderRadius: 4, marginRight: 7 },
  onlineDot: { backgroundColor: "#218A58" },
  offlineDot: { backgroundColor: "#D36A2E" },
  text: { fontSize: 12, fontWeight: "600", color: "#45534A" },
});