interface ISiteMetadataResult {
  siteTitle: string;
  siteUrl: string;
  description: string;
  keywords: string;
  logo: string;
  navLinks: {
    name: string;
    url: string;
  }[];
}

const data: ISiteMetadataResult = {
  siteTitle: '运动地图',
  siteUrl: '',
  logo: 'https://avatars.githubusercontent.com/u/87158446?v=4',
  description: 'Flyway的运动地图',
  keywords: 'workouts, running, cycling, riding, roadtrip, hiking, swimming',
  navLinks: [
    {
      name: '🏎️🚲🏃🏽‍♂️🚶🏽‍♂️🏕️',
      url: '',
    },
  ],
};

export default data;
