import { Head } from "expo-router/head";
import { Stack } from "expo-router";
import { StatusBar } from "expo-status-bar";

const OG_IMAGE = "https://images.unsplash.com/photo-1552664730-d307ca884978?auto=format&fit=crop&w=1200&q=80";

export default function RootLayout() {
  return (
    <>
      <Head>
        <title>Harsha Velagala | Meta Lead Ads Monitor</title>
        <meta name="description" content="Harsha Velagala's Meta Lead Ads monitor for live lead tracking and real-time updates from the backend." />
        <meta property="og:title" content="Harsha Velagala | Meta Lead Ads Monitor" />
        <meta property="og:description" content="Live Meta Lead Ads monitoring by Harsha Velagala, showing incoming lead submissions in real time." />
        <meta property="og:type" content="website" />
        <meta property="og:url" content="https://example.com" />
        <meta property="og:image" content={OG_IMAGE} />
        <meta property="og:image:width" content="1200" />
        <meta property="og:image:height" content="630" />
        <meta name="twitter:card" content="summary_large_image" />
        <meta name="twitter:title" content="Harsha Velagala | Meta Lead Ads Monitor" />
        <meta name="twitter:description" content="Live Meta Lead Ads monitoring by Harsha Velagala, showing incoming lead submissions in real time." />
        <meta name="twitter:image" content={OG_IMAGE} />
      </Head>
      <StatusBar style="dark" />
      <Stack screenOptions={{ headerShown: false }} />
    </>
  );
}
