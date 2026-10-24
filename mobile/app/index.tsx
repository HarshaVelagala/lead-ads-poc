import React, { useEffect, useState } from "react";
import { FlatList, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import EmptyState from "../components/EmptyState";
import LeadCard from "../components/LeadCard";
import LeadsHeader from "../components/LeadsHeader";
import LoadingState from "../components/LoadingState";
import { connectToLeadUpdates, fetchLeads } from "../services/leads";
import { Lead } from "../types/lead";

export default function LeadsScreen() {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | undefined>();

  useEffect(() => {
    let active = true;
    let disconnect = () => {};

    fetchLeads()
      .then((storedLeads) => {
        if (!active) return;
        setLeads(storedLeads);
      })
      .catch(() => {
        if (active) setError("Backend unavailable");
      })
      .finally(() => {
        if (!active) return;
        setIsLoading(false);
        disconnect = connectToLeadUpdates(
          (lead) => {
            setLeads((current) => [lead, ...current.filter((item) => item.id !== lead.id)]);
          },
          (connected) => {
            setIsConnected(connected);
            if (connected) {
              setError(undefined);
              fetchLeads().then((latestLeads) => {
                if (!active) return;
                setLeads((current) => {
                  const byId = new Map(current.map((lead) => [lead.id, lead]));
                  latestLeads.forEach((lead) => byId.set(lead.id, lead));
                  return Array.from(byId.values());
                });
              }).catch(() => {
                if (active) setError("Backend API unavailable");
              });
            } else {
              setError("Live connection interrupted · reconnecting");
            }
          },
        );
      });

    return () => {
      active = false;
      disconnect();
    };
  }, []);

  return (
    <SafeAreaView style={styles.safeArea}>
      {isLoading ? <LoadingState /> : (
        <FlatList
          data={leads}
          keyExtractor={(item) => item.id}
          renderItem={({ item }) => <LeadCard lead={item} />}
          ListHeaderComponent={<LeadsHeader count={leads.length} connected={isConnected} error={error} />}
          ListEmptyComponent={<EmptyState />}
          contentContainerStyle={styles.listContent}
          showsVerticalScrollIndicator={false}
          ListFooterComponent={error ? (
            <View style={styles.errorBox}>
              <Text style={styles.errorText}>{error}. Confirm the backend URL and that FastAPI is running.</Text>
            </View>
          ) : null}
        />
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: "#F9FAFB",
  },
  listContent: {
    flexGrow: 1,
    paddingHorizontal: 16,
    paddingBottom: 24,
  },
  errorBox: {
    paddingVertical: 12,
  },
  errorText: {
    color: "#9A4D28",
    fontSize: 13,
    textAlign: "center",
  },
});
