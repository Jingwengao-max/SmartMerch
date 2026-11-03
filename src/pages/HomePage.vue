<script setup lang="ts">
import AppHeader from '@/components/layout/AppHeader.vue'
import AppFooter from '@/components/layout/AppFooter.vue'
import HeroSection from '@/components/home/HeroSection.vue'
import TransformationSection from '@/components/home/TransformationSection.vue'
import WorksGallery from '@/components/home/WorksGallery.vue'
import ProcessSection from '@/components/home/ProcessSection.vue'
import ManifestoSection from '@/components/home/ManifestoSection.vue'
</script>

<template>
  <div class="bg-paper text-ink">
    <AppHeader />
    <main>
      <HeroSection />
      <TransformationSection />
      <WorksGallery />
      <ProcessSection />
      <ManifestoSection />
    </main>
    <AppFooter />
  </div>
</template>
