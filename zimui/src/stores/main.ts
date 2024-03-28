import { defineStore } from 'pinia'
import axios, { AxiosError }from 'axios'
import Channel from '@/types/Channel'
import Topic from '@/types/Topic'

export type RootState = {
  channelData: Channel | null
  isLoading: boolean
  errorMessage: string
  error: AxiosError | null
}
export const useMainStore = defineStore('main', {
  state: () =>
    ({
      channelData: null,
      isLoading: false,
      errorMessage: '',
      error: null,
    }) as RootState,
  getters: {},
  actions: {
    async fetchChannel() {
      this.isLoading = true
      this.errorMessage = ''
      try {
        const response = await axios.get('./channel.json')
        this.isLoading = false
        this.channelData = response.data as Channel
      } catch (error) {
        this.isLoading = false
        this.channelData = null
        this.errorMessage = 'Failed to load channel data'
        this.error = error // Set axios error to store
      }
    },
    async fetchTopic(slug: string) {
      this.isLoading = true
      this.errorMessage = ''
      try {
        const response = await axios.get('./topics/' + slug + '.json')
        this.isLoading = false
        return response.data as Topic
      } catch (error) {
        this.isLoading = false
        this.channelData = null
        this.errorMessage = 'Failed to load node ' + slug + ' data'
        this.error = error // Set axios error to store
        return null
      }
    },
  },
})
